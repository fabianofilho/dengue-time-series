"""Confere o manuscrito contra paper/verified_numbers.json e contra o .bib.

Por que existe: o Results deste manuscrito passou meses dizendo que o sMAPE medio
do TimesFM era 75,3% (56,0 a 97,1) enquanto o abstract, a tabela gerada e o
verified_numbers.json diziam 74,6% (55,6 a 96,6). Os dois numeros estavam no
mesmo arquivo. Nenhuma checagem existente pegava isso: check_artifacts compara o
PDF com o .docx, e os dois herdavam o mesmo erro.

Confere tres coisas:
  citacoes  toda chave \\cite{...} do .tex existe no .bib, e o que sobra no .bib
  afirmacoes valores declarados abaixo batem com verified_numbers.json
  literais   numeros de coorte antigos que nao podem reaparecer em lugar nenhum

As afirmacoes sao uma lista curada, nao uma varredura automatica: casar numero
solto em prosa daria falso positivo demais para alguem levar a serio, e uma
checagem que ninguem leva a serio nao e checagem.

Uso:
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
TEXS = ["manuscript.tex", "manuscript_rsbmt.tex", "supplementary.tex"]

# Numeros de coorte que circularam e estao errados. Nenhum pode reaparecer.
LITERAIS_PROIBIDOS = {
    "1{,}452": "previsoes por modelo por cidade; o correto e 1.428",
    "1,452": "previsoes por modelo por cidade; o correto e 1.428",
    "1{,}212": "previsoes com intervalo; o correto e 1.188",
    "81{,}312": "previsoes no total; o correto e 79.968",
    "81,312": "previsoes no total; o correto e 79.968",
    "121 folds": "folds por cidade; o correto e 119",
    "180 monthly": "meses por cidade; o correto e 178",
    "14-year": "duracao da serie; fevereiro de 2010 a novembro de 2024 sao 15 anos",
    "14 years": "duracao da serie; fevereiro de 2010 a novembro de 2024 sao 15 anos",
    "Bozza": "sobrenome errado do primeiro autor; e Barcellos-Filho",
}

# O pacote de submissao repete as afirmacoes do manuscrito em prosa livre, e foi
# onde "81,312 total predictions" e "14-year benchmark" sobreviveram mais tempo:
# nenhuma checagem olhava para ca.
SUBMISSAO = "submission"


EXTENSO = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
    12: "twelve",
}


def n_de(n: int) -> list[str]:
    """As duas formas em que um numero pequeno aparece na prosa do manuscrito."""
    formas = [str(n)]
    if n in EXTENSO:
        formas.append(EXTENSO[n])
    return formas


def afirmacoes(v: dict) -> list[tuple[str, list[str], str]]:
    """(rotulo, formas aceitas, de onde o valor veio).

    Uma afirmacao passa se QUALQUER uma das formas aparece. O manuscrito escreve
    numero pequeno por extenso, e exigir o algarismo reprovava texto correto.
    """
    b = v["baseline"]
    g = v["global_models"]
    tf = v["mean_smape_by_model"]["timesfm"]
    lo, hi = v["timesfm_smape_range"]
    rel_lo, rel_hi = b["relmae_range"]
    c = b["criterion"]
    return [
        ("meses por cidade", [f"{v['n_months_per_city']} monthly observations"],
         "n_months_per_city"),
        ("folds", [f"{v['n_folds_per_city']} folds"], "n_folds_per_city"),
        ("previsoes por modelo", ["1{,}428"], "n_predictions_per_model_city"),
        ("previsoes no total", ["79{,}968"], "n_predictions_total"),
        ("sMAPE medio do timesfm", [f"{tf:.1f}"], "mean_smape_by_model.timesfm"),
        ("faixa do timesfm, minimo", [f"{lo}"], "timesfm_smape_range[0]"),
        ("faixa do timesfm, maximo", [f"{hi}"], "timesfm_smape_range[1]"),
        ("RelMAE minimo", [f"{rel_lo}"], "baseline.relmae_range[0]"),
        ("RelMAE maximo", [f"{rel_hi}"], "baseline.relmae_range[1]"),
        ("limiar do criterio",
         [f"{a} of the {b}" for a in n_de(c["min_horizontes"])
          for b in n_de(c["n_horizontes"])],
         "baseline.criterion"),
        ("replicas do bootstrap", ["10{,}000"], "baseline.bootstrap.B"),
        ("pares em que agrupar ajuda",
         [f"{a} of the {g['n_pairs']}" for a in n_de(g["grouping_helps"])],
         "global_models.grouping_helps"),
        ("vitorias do timesfm com os globais",
         [f"{a} of eight" for a in n_de(g["timesfm_wins_with_global_pool"])],
         "global_models.timesfm_wins_with_global_pool"),
    ]


def le(nome: str) -> str:
    return (PAPER / nome).read_text(encoding="utf-8")


def checa_citacoes(problemas: list[str]) -> None:
    bib = BIB.read_text(encoding="utf-8")
    chaves = set(re.findall(r"@\w+\{([^,]+),", bib))
    padrao = re.compile(r"\\cite[a-zA-Z]*\{([^}]+)\}")
    usadas: set[str] = set()
    for nome in TEXS:
        for grupo in padrao.findall(le(nome)):
            usadas.update(k.strip() for k in grupo.split(","))
    faltando = sorted(usadas - chaves)
    if faltando:
        problemas.append(
            f"[citacoes] chaves citadas e ausentes do .bib: {', '.join(faltando)}"
        )
    else:
        print(f"  citacoes: {len(usadas)} chaves usadas, todas presentes no .bib")
    orfas = sorted(chaves - usadas)
    if orfas:
        print(f"  citacoes: {len(orfas)} entradas no .bib nunca citadas "
              f"({', '.join(orfas[:5])}{' ...' if len(orfas) > 5 else ''})")


def checa_literais(problemas: list[str]) -> None:
    achados = 0
    for nome in TEXS:
        texto = le(nome)
        for literal, porque in LITERAIS_PROIBIDOS.items():
            if literal in texto:
                problemas.append(f"[literal] {nome} contem '{literal}': {porque}")
                achados += 1
    outros = sorted((PAPER / "tables").glob("*.tex")) + sorted(
        (PAPER / SUBMISSAO).glob("*.md")
    )
    for arquivo in outros:
        texto = arquivo.read_text(encoding="utf-8")
        pasta = arquivo.parent.name
        for literal, porque in LITERAIS_PROIBIDOS.items():
            if literal in texto:
                problemas.append(
                    f"[literal] {pasta}/{arquivo.name} contem '{literal}': {porque}"
                )
                achados += 1
    if not achados:
        print(f"  literais: nenhum dos {len(LITERAIS_PROIBIDOS)} numeros antigos reapareceu")


def checa_cover_letter(v: dict, problemas: list[str]) -> None:
    """A carta repete os numeros do manuscrito em prosa. Confere os que mudam."""
    alvo = PAPER / SUBMISSAO / "cover_letter_rsbmt.md"
    if not alvo.exists():
        problemas.append(f"[carta] {alvo.name} ausente")
        return
    texto = alvo.read_text(encoding="utf-8")
    b = v["baseline"]
    g = v["global_models"]
    rel_lo, rel_hi = b["relmae_range"]
    exigidos = [
        (f"{rel_lo}", "RelMAE minimo"),
        (f"{rel_hi}", "RelMAE maximo"),
        (f"{v['mean_smape_by_model']['timesfm']:.1f}", "sMAPE medio do TimesFM"),
        (f"{v['n_folds_per_city']} folds", "folds por cidade"),
        (f"{n_de(g['timesfm_wins_with_global_pool'])[1]} of eight",
         "vitorias com os globais"),
    ]
    faltando = [rotulo for alvo_txt, rotulo in exigidos if alvo_txt not in texto]
    if faltando:
        problemas.append(
            f"[carta] cover_letter_rsbmt.md nao traz: {', '.join(faltando)}"
        )
    else:
        print(f"  carta: {len(exigidos)} numeros conferidos contra verified_numbers")


def checa_afirmacoes(v: dict, problemas: list[str]) -> None:
    principal = le("manuscript.tex")
    ok = 0
    for rotulo, formas, origem in afirmacoes(v):
        if any(f in principal for f in formas):
            ok += 1
        else:
            alternativas = " | ".join(repr(f) for f in formas)
            problemas.append(
                f"[afirmacao] manuscript.tex nao contem {alternativas} "
                f"({rotulo}, de {origem})"
            )
    print(f"  afirmacoes: {ok} de {len(afirmacoes(v))} presentes no manuscrito")


def main() -> int:
    if not NUMBERS.exists():
        print(f"[ERRO] {NUMBERS} ausente. Rode scripts/build_paper_assets.py.",
              file=sys.stderr)
        return 1
    v = json.loads(NUMBERS.read_text(encoding="utf-8"))

    print("Conferindo o manuscrito contra verified_numbers.json e o .bib")
    problemas: list[str] = []
    checa_citacoes(problemas)
    checa_literais(problemas)
    checa_afirmacoes(v, problemas)
    checa_cover_letter(v, problemas)

    if problemas:
        print()
        print(f"[ERRO] {len(problemas)} divergencia(s):")
        for p in problemas:
            print(f"  {p}")
        return 1
    print()
    print("Sem divergencia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
