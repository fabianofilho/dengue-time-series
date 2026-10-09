"""Confere o manuscrito de submissao contra paper/verified_numbers.json e contra o .bib.

Por que existe: o Results deste manuscrito passou meses dizendo que o sMAPE medio
do TimesFM era 75,3% (56,0 a 97,1) enquanto o abstract, a tabela gerada e o
verified_numbers.json diziam 74,6% (55,6 a 96,6). E o .docx de revisao de
06/10/2026 dizia que o TimesFM era o melhor por MAE em todas as cidades, quando
em Brasilia o melhor e o CatBoost. Desde 09/10/2026 o texto mora numa fonte so
(paper/plos/manuscript_src.tex) e os numeros entram por expressao, mas a fonte
ainda pode afirmar algo que a expressao nao sustenta; esta checagem olha o
resultado renderizado.

Confere cinco coisas:
  citacoes   toda chave \\cite{...} da fonte existe no .bib
  literais   numeros e nomes antigos que nao podem reaparecer
  afirmacoes valores declarados abaixo aparecem no manuscrito renderizado
  intervalos o IC de cada celula da Tabela 2 bate com verified_numbers.json
  carta      a cover letter traz os numeros que repete do manuscrito

Uso (depois de scripts/build_plos.py):
    python scripts/check_numbers.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
NUMBERS = PAPER / "verified_numbers.json"
BIB = PAPER / "refs" / "references.bib"
SRC = PAPER / "plos" / "manuscript_src.tex"
RENDER = ROOT / "build" / "plos" / "manuscript.tex"
CARTA = PAPER / "submission" / "cover_letter.md"
CAMPOS = PAPER / "plos" / "submission_fields.md"

# Numeros e nomes que circularam e estao errados. Nenhum pode reaparecer.
LITERAIS_PROIBIDOS = {
    "1,452": "previsoes por modelo por cidade; o correto e 1.428",
    "1,212": "previsoes com intervalo; o correto e 1.188",
    "81,312": "previsoes no total; o correto e 79.968",
    "121 folds": "folds por cidade; o correto e 119",
    "180 monthly": "meses por cidade; o correto e 178",
    "14-year": "duracao da serie; fevereiro de 2010 a novembro de 2024 sao 15 anos",
    "14 years": "duracao da serie; fevereiro de 2010 a novembro de 2024 sao 15 anos",
    "Bozza": "sobrenome errado do primeiro autor; o nome e Fabiano Novaes Barcellos Filho",
    "Barcellos-Filho": "o sobrenome nao leva hifen: Barcellos Filho",
    "Google DeepMind": "o TimesFM foi desenvolvido pela Google Research",
    "fabiano.nb@gmail.com": "no manuscrito o e-mail do autor correspondente e o da USP",
    "2,000 replicates": "IC antigo por previsao isolada; o bootstrap e por janela, B = 10.000",
}

EXTENSO = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
           7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def n_de(n: int) -> list[str]:
    """As duas formas em que um numero pequeno aparece na prosa."""
    return [str(n)] + ([EXTENSO[n]] if n in EXTENSO else [])


def afirmacoes(v: dict) -> list[tuple[str, list[str], str]]:
    """(rotulo, formas aceitas, de onde o valor veio). Passa se QUALQUER forma aparece."""
    b, g, c = v["baseline"], v["global_models"], v["baseline"]["criterion"]
    tf = v["mean_smape_by_model"]["timesfm"]
    lo, hi = v["timesfm_smape_range"]
    rel_lo, rel_hi = b["relmae_range"]
    mae_tf = sum(1 for r in v["metric_disagreement"] if r["mae"] == "timesfm")
    ex = v["exploratory_log"]
    return [
        ("meses por cidade", [f"{v['n_months_per_city']} monthly observations"],
         "n_months_per_city"),
        ("folds", [f"{v['n_folds_per_city']} folds"], "n_folds_per_city"),
        ("previsoes por modelo", [f"{v['n_predictions_per_model_city']:,}"],
         "n_predictions_per_model_city"),
        ("previsoes no total", [f"{v['n_predictions_total']:,}"], "n_predictions_total"),
        ("sMAPE medio do timesfm", [f"{tf:.1f}"], "mean_smape_by_model.timesfm"),
        ("faixa do timesfm, minimo", [f"{lo}"], "timesfm_smape_range[0]"),
        ("faixa do timesfm, maximo", [f"{hi}"], "timesfm_smape_range[1]"),
        ("RelMAE minimo", [f"{rel_lo}"], "baseline.relmae_range[0]"),
        ("RelMAE maximo", [f"{rel_hi}"], "baseline.relmae_range[1]"),
        ("limiar do criterio",
         [f"{a} of the {b_}" for a in n_de(c["min_horizontes"]) for b_ in n_de(c["n_horizontes"])],
         "baseline.criterion"),
        ("replicas do bootstrap", [f"{b['bootstrap']['B']:,}"], "baseline.bootstrap.B"),
        ("pares em que agrupar ajuda",
         [f"{a} of the {g['n_pairs']}" for a in n_de(g["grouping_helps"])],
         "global_models.grouping_helps"),
        ("vitorias do timesfm por MAE",
         [f"first in {a} of {b_}" for a in n_de(mae_tf) for b_ in n_de(v["n_cities"])],
         "metric_disagreement"),
        ("RelMAE medio do TimesFM, exploratorio",
         [f"{ex['mean_relmae']['timesfm']:.3f}"], "exploratory_log.mean_relmae.timesfm"),
        ("pares confirmados, exploratorio",
         [f"{ex['timesfm_vs_log_confirmed']} of {ex['timesfm_vs_log_pairs']}"],
         "exploratory_log"),
    ]


def checa_citacoes(problemas: list[str]) -> None:
    bib = BIB.read_text(encoding="utf-8")
    chaves = set(re.findall(r"@\w+\{([^,]+),", bib))
    usadas: set[str] = set()
    for grupo in re.findall(r"\\cite[a-zA-Z]*\{([^}]+)\}", SRC.read_text(encoding="utf-8")):
        usadas.update(k.strip() for k in grupo.split(","))
    faltando = sorted(usadas - chaves)
    if faltando:
        problemas.append(f"[citacoes] chaves citadas e ausentes do .bib: {', '.join(faltando)}")
    else:
        print(f"  citacoes: {len(usadas)} chaves usadas, todas presentes no .bib")
    orfas = sorted(chaves - usadas)
    if orfas:
        print(f"  citacoes: {len(orfas)} entrada(s) no .bib nunca citada(s): {', '.join(orfas)}")


def checa_literais(problemas: list[str]) -> None:
    alvos = [RENDER, SRC, CARTA, CAMPOS] + sorted((PAPER / "tables").glob("*.tex"))
    achados = 0
    for arq in alvos:
        if not arq.exists():
            continue
        texto = arq.read_text(encoding="utf-8")
        for literal, porque in LITERAIS_PROIBIDOS.items():
            if literal in texto:
                problemas.append(f"[literal] {arq.relative_to(ROOT)} contem '{literal}': {porque}")
                achados += 1
    if not achados:
        print(f"  literais: nenhum dos {len(LITERAIS_PROIBIDOS)} valores antigos reapareceu")


def checa_afirmacoes(v: dict, texto: str, problemas: list[str]) -> None:
    ok = 0
    for rotulo, formas, origem in afirmacoes(v):
        if any(f in texto for f in formas):
            ok += 1
        else:
            alternativas = " | ".join(repr(f) for f in formas)
            problemas.append(f"[afirmacao] manuscrito nao contem {alternativas} ({rotulo}, de {origem})")
    print(f"  afirmacoes: {ok} de {len(afirmacoes(v))} presentes no manuscrito")


def checa_intervalos(v: dict, problemas: list[str]) -> None:
    """Cada IC da Tabela 2 contra verified_numbers.json, celula a celula."""
    t2 = (PAPER / "tables" / "table2_smape.tex").read_text(encoding="utf-8")
    ordem = ["timesfm", "catboost", "xgboost", "randomforest", "sarimax", "ridge", "lgbm"]
    n, erros = 0, 0
    for cidade, por_modelo in v["per_city"].items():
        m = re.search(re.escape(cidade) + r" &[^\n]*\n([^\n]*)", t2)
        if not m:
            problemas.append(f"[intervalo] Tabela 2 sem linha para {cidade}")
            continue
        achados = re.findall(r"\(([\d.]+), ([\d.]+)\)", m.group(1))
        for modelo, (lo, hi) in zip(ordem, achados):
            elo, ehi = por_modelo[modelo]["sMAPE_CI"]
            n += 1
            # verified guarda 2 casas e a tabela arredonda o valor cheio para 1:
            # 122.55 vira 122.5 num e 122.6 no outro. Tolerancia de meia casa.
            if abs(float(lo) - elo) > 0.051 or abs(float(hi) - ehi) > 0.051:
                erros += 1
                problemas.append(f"[intervalo] {cidade}/{modelo}: tabela ({lo}, {hi}), "
                                 f"verified ({elo:.1f}, {ehi:.1f})")
    if not erros:
        print(f"  intervalos: {n} ICs da Tabela 2 batem com verified_numbers.json")


def checa_carta(v: dict, problemas: list[str]) -> None:
    if not CARTA.exists():
        problemas.append(f"[carta] {CARTA.relative_to(ROOT)} ausente")
        return
    texto = CARTA.read_text(encoding="utf-8")
    b = v["baseline"]
    exigidos = [
        (f"{b['relmae_range'][0]}", "RelMAE minimo"),
        (f"{b['relmae_range'][1]}", "RelMAE maximo"),
        (f"{v['n_predictions_total']:,}", "previsoes no total"),
        (f"{v['exploratory_log']['mean_relmae']['timesfm']:.3f}", "RelMAE do TimesFM"),
        (f"{v['exploratory_log']['mean_relmae']['catboost_log']:.3f}", "RelMAE do CatBoost log"),
    ]
    faltando = [rotulo for alvo, rotulo in exigidos if alvo not in texto]
    if faltando:
        problemas.append(f"[carta] cover_letter.md nao traz: {', '.join(faltando)}")
    else:
        print(f"  carta: {len(exigidos)} numeros conferidos contra verified_numbers")


def main() -> int:
    if not NUMBERS.exists():
        print(f"[ERRO] {NUMBERS} ausente. Rode scripts/build_paper_assets.py.", file=sys.stderr)
        return 1
    if not RENDER.exists() or RENDER.stat().st_mtime < SRC.stat().st_mtime:
        print("[ERRO] manuscrito renderizado ausente ou mais velho que a fonte. "
              "Rode scripts/build_plos.py.", file=sys.stderr)
        return 1
    v = json.loads(NUMBERS.read_text(encoding="utf-8"))
    texto = RENDER.read_text(encoding="utf-8")

    print("Conferindo o manuscrito contra verified_numbers.json e o .bib")
    problemas: list[str] = []
    checa_citacoes(problemas)
    checa_literais(problemas)
    checa_afirmacoes(v, texto, problemas)
    checa_intervalos(v, problemas)
    checa_carta(v, problemas)

    if problemas:
        print(f"\n[ERRO] {len(problemas)} divergencia(s):")
        for p in problemas:
            print(f"  {p}")
        return 1
    print("\nSem divergencia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
