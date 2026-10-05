"""Incerteza do benchmark por cidade: bootstrap pareado de janelas, Diebold-Mariano e veredito.

Responde a pergunta que o benchmark publicado nao responde: algum dos sete
modelos bate o piso sazonal, e isso sobrevive a um teste?

A regra de decisao nao mora aqui. Ela esta em results/criterion.json, que foi
gravado e commitado antes desta primeira execucao. Este script le aquele
arquivo, nao aceita criterio por linha de comando, e recusa rodar se o arquivo
nao existir. E o unico jeito de a ordem "criterio antes do resultado" ser
verificavel por quem so tem o repositorio.

Desenho da reamostragem, herdado de onco_timeseries: as previsoes de um rolling
origin nao sao independentes. As 119 janelas se sobrepoem e, dentro de cada uma,
os 12 horizontes compartilham a mesma origem de treino. Por isso a unidade de
reamostragem e a JANELA INTEIRA, e o mesmo sorteio serve todos os modelos e
todas as metricas, o que mantem o pareamento.

Uso:
  python scripts/run_uncertainty.py                    # as 8 cidades
  python scripts/run_uncertainty.py --cities manaus    # uma cidade
"""
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from dengue_forecast.global_models import LOCAL_COUNTERPART
from dengue_forecast.uncertainty import (
    bootstrap_metrica,
    dm_test,
    ic_percentil,
    p_bicaudal,
    sortear_janelas,
)

ROOT = Path(__file__).resolve().parents[1]

CITIES = [
    "sao_paulo",
    "rio",
    "belo_horizonte",
    "brasilia",
    "fortaleza",
    "recife",
    "manaus",
    "salvador",
]

BASELINE = "seasonal_naive"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", default=str(ROOT / "results"))
    p.add_argument("--cities", default="", help="Subconjunto de cidades, separadas por vírgula")
    p.add_argument(
        "--criterion",
        default=str(ROOT / "results" / "criterion.json"),
        help="Critério pré-declarado. Não há opção para sobrescrevê-lo por linha de comando.",
    )
    return p.parse_args()


def smape_vec(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """sMAPE ponto a ponto, em porcentagem. Mesmo eps de evaluate.smape."""
    return 200.0 * np.abs(y_pred - y_true) / (np.abs(y_true) + np.abs(y_pred) + eps)


def to_matrices(df: pd.DataFrame, models: list[str], n_win: int, n_hor: int) -> dict:
    """Empilha as previsões em matriz (janela x horizonte) por modelo."""
    out = {}
    for m in models:
        g = df[df.model == m].sort_values(["window", "horizon"])
        if len(g) != n_win * n_hor:
            raise ValueError(
                f"Modelo {m} tem {len(g)} previsões; esperado {n_win}x{n_hor}. "
                "O bootstrap pareado exige o mesmo conjunto de janelas para todos os modelos."
            )
        out[m] = {
            "y_true": g["y_true"].to_numpy().reshape(n_win, n_hor),
            "y_pred": g["y_pred"].to_numpy().reshape(n_win, n_hor),
        }
    return out


def analisa_cidade(
    city: str,
    preds_path: Path,
    crit: dict,
    results_dir: Path,
    escopo: list[str] | None = None,
    sufixo: str = "",
) -> dict:
    """Bootstrap, DM e veredito de uma cidade.

    `escopo` limita os modelos ao conjunto declarado. Sem isso, todo modelo que
    aparecesse no CSV entraria no veredito, e acrescentar uma variante
    exploratória mudaria em silêncio o veredito confirmatório (o melhor por
    RelMAE, a contagem de pares). `sufixo` separa os arquivos de cada conjunto.
    """
    df = pd.read_csv(preds_path, parse_dates=["date"])
    for col in ("model", "y_true", "y_pred", "window", "horizon"):
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente em {preds_path}: {col}")
    if escopo is not None:
        faltando = sorted(set(escopo) - set(df.model.unique()))
        if faltando:
            raise ValueError(f"{city}: modelos do escopo ausentes do CSV: {faltando}")
        df = df[df.model.isin(escopo)]

    models = sorted(df.model.unique())
    if BASELINE not in models:
        raise ValueError(f"{city}: {BASELINE} ausente do CSV. Rode o baseline antes.")

    n_win = int(df.window.max())
    n_hor = int(df.horizon.max())
    if n_hor != crit["criterio"]["n_horizontes"]:
        raise ValueError(
            f"{city}: CSV tem {n_hor} horizontes, critério declarou "
            f"{crit['criterio']['n_horizontes']}"
        )

    mats = to_matrices(df, models, n_win, n_hor)
    B = crit["bootstrap"]["B"]
    alpha = crit["criterio"]["alpha"]
    min_h = crit["criterio"]["min_horizontes"]

    # Perdas ponto a ponto, matriz (janela x horizonte) por modelo.
    ae = {m: np.abs(mats[m]["y_pred"] - mats[m]["y_true"]) for m in models}
    sm = {m: smape_vec(mats[m]["y_true"], mats[m]["y_pred"]) for m in models}

    # Um único sorteio, reusado por todos os modelos e métricas.
    idx = sortear_janelas(n_win, B, crit["bootstrap"]["seed"])

    boot_ae = {m: bootstrap_metrica(ae[m], idx) for m in models}
    boot_sm = {m: bootstrap_metrica(sm[m], idx) for m in models}

    # RelMAE: razão dentro de cada réplica, não razão das médias. É o que mantém
    # o pareamento: numerador e denominador são calculados sobre as MESMAS
    # janelas reamostradas.
    den_boot = boot_ae[BASELINE]
    boot_rel = {m: boot_ae[m] / den_boot for m in models}
    den_point = ae[BASELINE].mean()
    rel_point = {m: ae[m].mean() / den_point for m in models}

    metricas = {
        "relmae": (rel_point, boot_rel),
        "mae": ({m: ae[m].mean() for m in models}, boot_ae),
        "smape": ({m: sm[m].mean() for m in models}, boot_sm),
    }

    linhas = []
    for nome, (pontual, boot) in metricas.items():
        for m in models:
            lo, hi = ic_percentil(boot[m])
            linhas.append(
                {
                    "city": city,
                    "model": m,
                    "metric": nome,
                    "point": pontual[m],
                    "ci_low": lo,
                    "ci_high": hi,
                    "ci_width": hi - lo,
                    "n_windows": n_win,
                    "n_predictions": ae[m].size,
                    "B": B,
                }
            )
    boot_df = pd.DataFrame(linhas)
    boot_path = results_dir / f"uncertainty_{city}{sufixo}_bootstrap_metrics.csv"
    boot_df.to_csv(boot_path, index=False)

    # ---------------- diferenças pareadas e Diebold-Mariano ----------------
    pares = list(combinations(models, 2))
    linhas = []
    for a, b in pares:
        for nome, (pontual, boot) in metricas.items():
            boot_dif = boot[a] - boot[b]
            lo, hi = ic_percentil(boot_dif)
            linhas.append(
                {
                    "city": city,
                    "pair": f"{a}_menos_{b}",
                    "metric": nome,
                    "test": "bootstrap_pareado",
                    "horizon": "pooled",
                    "diff_point": pontual[a] - pontual[b],
                    "ci_low": lo,
                    "ci_high": hi,
                    "ci_contains_zero": bool(lo <= 0 <= hi),
                    "p_bootstrap": p_bicaudal(boot_dif),
                    "B": B,
                }
            )

    # DM sobre a perda relativa. Dividir a perda por uma constante positiva da
    # cidade não muda a estatística de DM, que é invariante a escala, então este
    # bloco é o mesmo teste que o DM sobre erro absoluto. Fica escrito na
    # métrica para o arquivo não sugerir que foram dois testes diferentes.
    dm_linhas = []
    for a, b in pares:
        for h in range(1, n_hor + 1):
            d = (ae[a][:, h - 1] - ae[b][:, h - 1]) / den_point
            estat, p = dm_test(d, h)
            dm_linhas.append(
                {
                    "city": city,
                    "pair": f"{a}_menos_{b}",
                    "metric": "relmae",
                    "test": "diebold_mariano_harvey",
                    "horizon": h,
                    "mean_loss_diff": float(d.mean()),
                    "dm_stat_harvey": estat,
                    "p_value": p,
                    "n_windows": n_win,
                }
            )
    dm_df = pd.DataFrame(dm_linhas)
    pair_df = pd.concat([pd.DataFrame(linhas), dm_df], ignore_index=True)
    pair_path = results_dir / f"uncertainty_{city}{sufixo}_pairwise_tests.csv"
    pair_df.to_csv(pair_path, index=False)

    # ---------------- veredito ----------------
    def veredito(metrica: str) -> dict:
        pontual, boot = metricas[metrica]
        itens = []
        for a, b in pares:
            boot_dif = boot[a] - boot[b]
            lo, hi = ic_percentil(boot_dif)
            exclui_zero = not (lo <= 0 <= hi)
            sub = dm_df[dm_df.pair == f"{a}_menos_{b}"]
            n_sig = int((sub.p_value < alpha).sum())
            itens.append(
                {
                    "par": f"{a}_menos_{b}",
                    "diferenca": round(float(pontual[a] - pontual[b]), 4),
                    "ic95": f"[{lo:.4f}, {hi:.4f}]",
                    "ic_exclui_zero": exclui_zero,
                    "dm_abaixo_alpha": f"{n_sig}/{n_hor}",
                    "confirmado": bool(exclui_zero and n_sig >= min_h),
                }
            )

        # As duas orientacoes importam. combinations() sobre nomes ordenados poe
        # o baseline como primeiro elemento nos pares com timesfm e xgboost, que
        # vem depois dele no alfabeto. Filtrar so por b == BASELINE deixaria de
        # fora justamente o modelo que lidera em 7 das 8 cidades.
        contra_baseline = []
        for it in itens:
            a, b = it["par"].split("_menos_")
            if BASELINE not in (a, b) or a == b:
                continue
            modelo = b if a == BASELINE else a
            # Sinal sempre na orientacao modelo menos baseline: negativo
            # significa que o modelo erra menos que o piso. O IC tem que virar
            # junto, com os limites trocados, senao o arquivo mostra diferenca
            # negativa ao lado de um intervalo positivo.
            inverte = a == BASELINE
            sinal = -1.0 if inverte else 1.0
            lo_r, hi_r = ic_percentil(boot[a] - boot[b])
            if inverte:
                lo_r, hi_r = -hi_r, -lo_r
            contra_baseline.append(
                {
                    **it,
                    "modelo": modelo,
                    "orientacao_do_par_bruto": it["par"],
                    "diferenca_modelo_menos_baseline": round(sinal * it["diferenca"], 4),
                    "ic95_modelo_menos_baseline": f"[{lo_r:.4f}, {hi_r:.4f}]",
                    "bate_o_baseline": bool(
                        it["confirmado"] and sinal * it["diferenca"] < 0
                    ),
                }
            )

        batem = [c["modelo"] for c in contra_baseline if c["bate_o_baseline"]]

        # Agrupar as cidades ajuda ou nao? A unica comparacao que responde isso
        # e entre o MESMO estimador nas duas formas. Comparar global_lgbm com
        # catboost misturaria o efeito de agrupar com o de trocar de estimador.
        por_par = {i["par"]: i for i in itens}
        local_vs_global = []
        for glob, local in sorted(LOCAL_COUNTERPART.items()):
            if glob not in models or local not in models:
                continue
            chave = f"{glob}_menos_{local}" if f"{glob}_menos_{local}" in por_par else f"{local}_menos_{glob}"
            it = por_par[chave]
            inverte = chave.startswith(f"{local}_menos_")
            sinal = -1.0 if inverte else 1.0
            a, b = chave.split("_menos_")
            lo_r, hi_r = ic_percentil(boot[a] - boot[b])
            if inverte:
                lo_r, hi_r = -hi_r, -lo_r
            dif = round(sinal * it["diferenca"], 4)
            local_vs_global.append(
                {
                    "estimador": local,
                    "global": glob,
                    "diferenca_global_menos_local": dif,
                    "ic95_global_menos_local": f"[{lo_r:.4f}, {hi_r:.4f}]",
                    "ic_exclui_zero": it["ic_exclui_zero"],
                    "dm_abaixo_alpha": it["dm_abaixo_alpha"],
                    "confirmado": it["confirmado"],
                    "agrupar_ajuda": bool(it["confirmado"] and dif < 0),
                    "agrupar_atrapalha": bool(it["confirmado"] and dif > 0),
                }
            )

        return {
            "metrica": metrica,
            "itens": itens,
            "contra_baseline": contra_baseline,
            "local_vs_global": local_vs_global,
            "pares_confirmados": f"{sum(i['confirmado'] for i in itens)}/{len(itens)}",
            "batem_o_baseline": sorted(batem),
            "agrupar_ajuda_em": sorted(
                c["estimador"] for c in local_vs_global if c["agrupar_ajuda"]
            ),
            "agrupar_atrapalha_em": sorted(
                c["estimador"] for c in local_vs_global if c["agrupar_atrapalha"]
            ),
        }

    metrica_crit = crit["criterio"]["metrica_bootstrap"]
    metrica_sens = crit["analise_de_sensibilidade"]["metrica"]

    v_crit = veredito(metrica_crit)
    v_sens = veredito(metrica_sens)

    melhor_rel = min(
        (m for m in models if m != BASELINE), key=lambda m: rel_point[m]
    )
    melhor_smape = min(
        (m for m in models if m != BASELINE), key=lambda m: sm[m].mean()
    )

    verdict = {
        "cidade": city,
        "criterio": crit["criterio"],
        "bootstrap": crit["bootstrap"],
        "n_janelas": n_win,
        "n_horizontes": n_hor,
        "baseline": BASELINE,
        "baseline_mae": round(float(den_point), 4),
        "baseline_smape": round(float(sm[BASELINE].mean()), 4),
        "relmae_por_modelo": {m: round(float(rel_point[m]), 4) for m in models},
        "melhor_por_relmae": melhor_rel,
        "relmae_do_melhor": round(float(rel_point[melhor_rel]), 4),
        "melhor_por_smape": melhor_smape,
        "smape_do_melhor": round(float(sm[melhor_smape].mean()), 4),
        "metrica_concorda": melhor_rel == melhor_smape,
        "veredito": v_crit,
        "analise_de_sensibilidade": {
            **v_sens,
            "status": "exploratoria",
            "aviso": crit["analise_de_sensibilidade"]["regra"],
        },
    }
    vpath = results_dir / f"criterion_verdict_{city}{sufixo}.json"
    vpath.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"  {city:<16} baseline MAE {den_point:>10.1f}  "
        f"melhor {melhor_rel:<14} RelMAE {rel_point[melhor_rel]:.3f}  "
        f"confirmados {v_crit['pares_confirmados']:<6} "
        f"piso: {v_crit['batem_o_baseline'] or 'nenhum'}  "
        f"agrupar ajuda: {v_crit['agrupar_ajuda_em'] or 'nenhum'}  "
        f"atrapalha: {v_crit['agrupar_atrapalha_em'] or 'nenhum'}"
    )
    return verdict


def main() -> int:
    args = parse_args()
    crit_path = Path(args.criterion)
    if not crit_path.exists():
        print(f"[ERRO] Critério pré-declarado ausente: {crit_path}", file=sys.stderr)
        print("       Fixe e commite o critério antes de rodar o teste.", file=sys.stderr)
        return 1
    crit = json.loads(crit_path.read_text(encoding="utf-8"))

    results_dir = Path(args.results_dir)
    cities = [c.strip() for c in args.cities.split(",") if c.strip()] or CITIES

    print(
        f"[INFO] Critério: {crit['criterio']['metrica_bootstrap']}, "
        f"alpha {crit['criterio']['alpha']}, "
        f"{crit['criterio']['min_horizontes']}/{crit['criterio']['n_horizontes']} horizontes, "
        f"B={crit['bootstrap']['B']:,}, semente {crit['bootstrap']['seed']}"
    )

    # Conjunto confirmatorio: exatamente os modelos declarados no criterio.
    escopo_conf = crit["escopo"]["modelos"]
    vereditos = []
    for city in cities:
        preds = results_dir / f"benchmark_{city}_predictions.csv"
        vereditos.append(analisa_cidade(city, preds, crit, results_dir, escopo=escopo_conf))

    # Conjunto exploratorio da emenda de 2026-10-04: variantes _log ao lado dos
    # modelos brutos correspondentes, do TimesFM e do piso. Arquivos proprios.
    logs = crit["escopo"].get("modelos_exploratorios_log", [])
    if logs:
        escopo_exp = [BASELINE, "timesfm"] + [m[:-4] for m in logs] + logs
        print("\n[INFO] Analise EXPLORATORIA (variantes _log, emenda de 2026-10-04)")
        exp = []
        for city in cities:
            preds = results_dir / f"benchmark_{city}_predictions.csv"
            exp.append(
                analisa_cidade(city, preds, crit, results_dir, escopo=escopo_exp, sufixo="_exploratorio_log")
            )
        (results_dir / "criterion_summary_exploratorio_log.json").write_text(
            json.dumps(
                {
                    "status": "EXPLORATORIA: emenda feita depois de ver resultados; nao substitui o veredito confirmatorio",
                    "escopo": escopo_exp,
                    "cidades": [
                        {
                            "cidade": v["cidade"],
                            "relmae_por_modelo": v["relmae_por_modelo"],
                            "melhor_por_relmae": v["melhor_por_relmae"],
                            "melhor_por_smape": v["melhor_por_smape"],
                            "batem_o_baseline": v["veredito"]["batem_o_baseline"],
                        }
                        for v in exp
                    ],
                    "cidades_em_que_algum_modelo_bate_o_baseline": sum(
                        1 for v in exp if v["veredito"]["batem_o_baseline"]
                    ),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    resumo = {
        "criterio": crit["criterio"],
        "bootstrap": crit["bootstrap"],
        "cidades": [
            {
                "cidade": v["cidade"],
                "melhor_por_relmae": v["melhor_por_relmae"],
                "relmae_do_melhor": v["relmae_do_melhor"],
                "melhor_por_smape": v["melhor_por_smape"],
                "metrica_concorda": v["metrica_concorda"],
                "pares_confirmados": v["veredito"]["pares_confirmados"],
                "batem_o_baseline": v["veredito"]["batem_o_baseline"],
                "agrupar_ajuda_em": v["veredito"]["agrupar_ajuda_em"],
                "agrupar_atrapalha_em": v["veredito"]["agrupar_atrapalha_em"],
                "local_vs_global": {
                    x["estimador"]: x for x in v["veredito"]["local_vs_global"]
                },
                "relmae_globais": {
                    m: r
                    for m, r in v["relmae_por_modelo"].items()
                    if m.startswith("global_")
                },
                "batem_o_baseline_sensibilidade_smape": v["analise_de_sensibilidade"][
                    "batem_o_baseline"
                ],
            }
            for v in vereditos
        ],
    }
    n_cidades_com_vencedor = sum(1 for v in vereditos if v["veredito"]["batem_o_baseline"])
    resumo["resposta"] = {
        "pergunta": crit["pergunta"],
        "cidades_em_que_algum_modelo_bate_o_baseline": n_cidades_com_vencedor,
        "de_um_total_de": len(vereditos),
    }
    (results_dir / "criterion_summary.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print()
    print(
        f"[RESPOSTA] Algum modelo bate o {BASELINE} pelo critério em "
        f"{n_cidades_com_vencedor} de {len(vereditos)} cidades."
    )
    print(f"[INFO] Gravado: {results_dir / 'criterion_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
