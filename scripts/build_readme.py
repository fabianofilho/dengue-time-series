"""Regrava os blocos numéricos do README a partir dos artefatos de results/.

Por que isto existe: o README ficou meses anunciando CatBoost como vencedor com
MAE 9.892 e 1.452 previsões por modelo, seis modelos sem o TimesFM e período de
janeiro/2010 a dezembro/2024. Nenhum desses números sobreviveu à correção da
agregação mensal, e nenhum deles estava errado por descuido: estavam errados
porque eram digitados, e texto digitado não acompanha um reprocessamento.

Agora os blocos entre os marcadores sao gerados. Rode depois de
build_paper_assets.py e de run_uncertainty.py.

Uso:
  python scripts/build_readme.py
  python scripts/build_readme.py --check   # falha se o README estiver desatualizado
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
VERIFIED = ROOT / "paper" / "verified_numbers.json"
SUMMARY = ROOT / "results" / "criterion_summary.json"

CITY_LABEL = {
    "sao_paulo": "São Paulo",
    "rio": "Rio de Janeiro",
    "belo_horizonte": "Belo Horizonte",
    "brasilia": "Brasília",
    "fortaleza": "Fortaleza",
    "recife": "Recife",
    "manaus": "Manaus",
    "salvador": "Salvador",
}
MODEL_LABEL = {
    "timesfm": "TimesFM",
    "catboost": "CatBoost",
    "xgboost": "XGBoost",
    "randomforest": "Random Forest",
    "sarimax": "SARIMAX",
    "ridge": "Ridge",
    "lgbm": "LightGBM",
    "seasonal_naive": "Naive sazonal",
    "global_lgbm": "LightGBM global",
    "global_xgboost": "XGBoost global",
    "global_catboost": "CatBoost global",
    "global_randomforest": "Random Forest global",
    "global_ridge": "Ridge global",
}

ESTIMADORES = ["catboost", "lgbm", "randomforest", "ridge", "xgboost"]

MES = {
    "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
    "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
    "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro",
}


def milhar(n: int) -> str:
    """Separador de milhar do português. Existe como funcao porque aplicar
    .replace(",", ".") no fim de uma f-string implicitamente concatenada aplica
    ao paragrafo inteiro, e nao so ao numero: foi assim que toda virgula do
    bloco do baseline virou ponto na primeira geracao deste README."""
    return f"{n:,}".replace(",", ".")


def periodo_por_extenso(study_period: str) -> str:
    ini, fim = study_period.split(" to ")
    ay, am = ini.split("-")
    by, bm = fim.split("-")
    return f"{MES[am]}/{ay} a {MES[bm]}/{by}"


def bloco_coorte(v: dict) -> str:
    return "\n".join(
        [
            f"- **Período**: {periodo_por_extenso(v['study_period'])} "
            f"({v['n_months_per_city']} meses por cidade)",
            f"- **Cidades**: {v['n_cities']}",
            f"- **Modelos**: {v['n_models']} do artigo, mais o naive sazonal como piso",
            f"- **Backtesting**: rolling origin com janela expansiva, horizonte "
            f"{v['horizon_months']} meses, treino mínimo {v['min_train_size']} meses, passo 1 mês",
            f"- **Folds por cidade**: {v['n_folds_per_city']}",
            f"- **Previsões por modelo por cidade**: {milhar(v['n_predictions_per_model_city'])}",
            f"- **Previsões no total** ({v['n_models']} modelos x {v['n_cities']} cidades): "
            f"{milhar(v['n_predictions_total'])}",
            "- **Métricas**: MAE, RMSE e sMAPE",
        ]
    )


def bloco_modelos(v: dict) -> str:
    ordem = sorted(v["mean_smape_by_model"], key=lambda m: v["mean_smape_by_model"][m])
    linhas = [
        "| Modelo | sMAPE médio | sMAPE mediano | Cidades em que lidera (sMAPE) |",
        "|---|---:|---:|---:|",
    ]
    for m in ordem:
        linhas.append(
            f"| {MODEL_LABEL[m]} | {v['mean_smape_by_model'][m]:.2f} | "
            f"{v['median_smape_by_model'][m]:.2f} | "
            f"{v['cities_ranked_first_by_model'][m]}/{v['n_cities']} |"
        )
    return "\n".join(linhas)


def bloco_baseline(v: dict, s: dict) -> str:
    b = v["baseline"]
    crit = b["criterion"]
    linhas = [
        "| Cidade | Melhor modelo (RelMAE) | RelMAE | Melhor por sMAPE | Métricas concordam | Pares confirmados | Bate o piso |",
        "|---|---|---:|---|:-:|---:|---|",
    ]
    for c in s["cidades"]:
        batem = c["batem_o_baseline"]
        linhas.append(
            f"| {CITY_LABEL[c['cidade']]} | {MODEL_LABEL[c['melhor_por_relmae']]} | "
            f"{c['relmae_do_melhor']:.3f} | {MODEL_LABEL[c['melhor_por_smape']]} | "
            f"{'sim' if c['metrica_concorda'] else 'não'} | {c['pares_confirmados']} | "
            f"{', '.join(MODEL_LABEL[m] for m in batem) if batem else 'nenhum'} |"
        )
    tabela = "\n".join(linhas)

    n_ok = b["cities_where_any_model_beats_baseline"]
    n_tot = b["cities_total"]
    # Conta do proprio escopo do criterio, sem o piso, em vez de reusar
    # n_models, que e o numero de modelos DO ARTIGO e nao inclui os globais.
    n_modelos = len([m for m in b["scope_models"] if m != "seasonal_naive"])
    discord = sum(1 for c in s["cidades"] if not c["metrica_concorda"])

    texto = [
        f"Critério pré-declarado em [`results/criterion.json`](results/criterion.json), "
        f"gravado e commitado antes da primeira execução do teste. Um par conta como "
        f"confirmado quando o IC95% da diferença pareada por bootstrap exclui zero **e** o "
        f"teste de Diebold-Mariano com correção de Harvey tem p < {crit['alpha']} em pelo "
        f"menos {crit['min_horizontes']} dos {crit['n_horizontes']} horizontes. "
        f"Bootstrap pareado de janelas inteiras, B = {milhar(b['bootstrap']['B'])}, "
        f"semente {b['bootstrap']['seed']}.",
        "",
        "RelMAE é o MAE do modelo dividido pelo MAE do naive sazonal da mesma cidade. "
        "Abaixo de 1 significa que o modelo erra menos que o piso. Não é o MASE do livro, "
        "cujo denominador é o erro do naive dentro da amostra de treino.",
        "",
        tabela,
        "",
        f"**Resposta: nenhum dos {n_modelos} modelos bate o naive sazonal por este "
        f"critério, em {n_ok} de {n_tot} cidades.** O ponto estimado favorece o melhor "
        f"modelo em todas as cidades, mas o teste de Diebold-Mariano não acompanha: ele "
        f"fica bem abaixo dos {crit['min_horizontes']} horizontes exigidos. A análise de "
        f"sensibilidade em sMAPE, rotulada como exploratória, dá o mesmo veredito nas "
        f"{n_tot} cidades, mas troca o modelo vencedor em {discord} delas.",
    ]
    return "\n".join(texto)


def bloco_localglobal(v: dict, s: dict) -> str:
    b = v["baseline"]
    linhas = [
        "| Cidade | " + " | ".join(MODEL_LABEL[e] for e in ESTIMADORES) + " |",
        "|---|" + "---:|" * len(ESTIMADORES),
    ]
    ajuda = atrapalha = 0
    for c in s["cidades"]:
        celulas = []
        for e in ESTIMADORES:
            x = c["local_vs_global"][e]
            marca = "\\*" if x["confirmado"] else ""
            if x["agrupar_ajuda"]:
                ajuda += 1
            if x["agrupar_atrapalha"]:
                atrapalha += 1
            celulas.append(f"{x['diferenca_global_menos_local']:+.3f}{marca}")
        linhas.append(f"| {CITY_LABEL[c['cidade']]} | " + " | ".join(celulas) + " |")
    tabela = "\n".join(linhas)
    total = len(ESTIMADORES) * len(s["cidades"])

    return "\n".join(
        [
            "Diferença de RelMAE, modelo global menos modelo local do mesmo estimador. "
            "Negativo significa que agrupar as 8 cidades num modelo só ajudou. O asterisco "
            "marca os pares confirmados pelo mesmo critério pré-declarado; sem asterisco o "
            "sinal é ponto estimado e não passa no teste.",
            "",
            "Comparar global de um estimador com local de outro misturaria o efeito de "
            "agrupar com o de trocar de estimador, então a tabela é sempre o mesmo "
            "estimador nas duas formas.",
            "",
            tabela,
            "",
            f"**Agrupar ajudou de forma confirmada em {ajuda} de {total} pares "
            f"cidade-estimador, e atrapalhou em {atrapalha}.** Nos outros "
            f"{total - ajuda - atrapalha} o teste não distingue as duas formas. "
            "Nenhum modelo global bate o naive sazonal, e em várias cidades eles ficam "
            "bem acima dele: no Rio o melhor global tem RelMAE "
            f"{min(v['baseline']['relmae_global_by_city']['rio'].values()):.2f}, "
            "ou seja, erra bem mais que repetir o ano anterior.",
        ]
    )


BLOCOS = {
    "COORTE": bloco_coorte,
    "MODELOS": bloco_modelos,
    "BASELINE": bloco_baseline,
    "LOCALGLOBAL": bloco_localglobal,
}


def render(texto: str, v: dict, s: dict) -> str:
    for nome, fn in BLOCOS.items():
        ini = f"<!-- BEGIN {nome} (gerado por scripts/build_readme.py, nao editar a mao) -->"
        fim = f"<!-- END {nome} -->"
        if ini not in texto or fim not in texto:
            raise ValueError(f"Marcadores de {nome} ausentes no README")
        i = texto.index(ini) + len(ini)
        j = texto.index(fim)
        conteudo = fn(v) if fn is bloco_modelos or fn is bloco_coorte else fn(v, s)
        texto = texto[:i] + "\n" + conteudo + "\n" + texto[j:]
    return texto


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    for caminho, quem in ((VERIFIED, "build_paper_assets.py"), (SUMMARY, "run_uncertainty.py")):
        if not caminho.exists():
            print(f"[ERRO] {caminho} ausente. Rode scripts/{quem} antes.", file=sys.stderr)
            return 1

    v = json.loads(VERIFIED.read_text(encoding="utf-8"))
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))

    atual = README.read_text(encoding="utf-8")
    novo = render(atual, v, s)

    if args.check:
        if atual != novo:
            print("[ERRO] README desatualizado. Rode scripts/build_readme.py.", file=sys.stderr)
            return 1
        print("README em dia com results/.")
        return 0

    README.write_text(novo, encoding="utf-8", newline="\n")
    print("README.md regravado a partir de paper/verified_numbers.json e results/criterion_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
