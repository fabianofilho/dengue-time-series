"""
Mede o manuscrito contra os limites do journal alvo.

Journal alvo atual: Revista da Sociedade Brasileira de Medicina Tropical,
Artigo Original. Limites conferidos em sbmt.org.br/instrucoes-para-autores:
3.500 palavras de texto (excluindo resumo, titulo, referencias e ilustracoes),
resumo estruturado de ate 250 palavras, e ate 5 ilustracoes somando tabelas e
figuras.

Uso:
    python scripts/check_limits.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
TEX = ROOT / "paper" / (sys.argv[1] if len(sys.argv) > 1 else "manuscript_rsbmt.tex")

LIMITS = {
    "resumo (palavras)": 250,
    "corpo (palavras)": 3500,
    "ilustracoes (tabelas + figuras)": 5,
}


def word_count(tex: str) -> int:
    """Palavras de prosa, descartando comandos e argumentos de LaTeX."""
    t = re.sub(r"(?m)%.*$", "", tex)
    t = re.sub(r"\\(cite[a-z]*|ref|label|url|input|includegraphics)\{[^}]*\}", " X ", t)
    t = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}$\\~^_&]", " ", t)
    return len(re.findall(r"[A-Za-z][A-Za-z'-]*", t))


def main() -> None:
    s = TEX.read_text(encoding="utf-8")

    abstract = s[s.index(r"\begin{abstract}"): s.index(r"\end{abstract}")]
    body = s[s.index(r"\section{Introduction}"): s.index(r"\section*{Declarations}")]
    # \input de tabela e \includegraphics sao ilustracao, nao texto corrido
    body_only = re.sub(r"\\input\{tables[^}]*\}", "", body)
    body_only = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", body_only, flags=re.S)

    tables = len(re.findall(r"\\input\{tables/", s))
    figures = len(re.findall(r"\\includegraphics", s))

    actual = {
        "resumo (palavras)": word_count(abstract),
        "corpo (palavras)": word_count(body_only),
        "ilustracoes (tabelas + figuras)": tables + figures,
    }

    print("Revista da Sociedade Brasileira de Medicina Tropical, Artigo Original")
    print(f"{'item':34s} {'atual':>8s} {'limite':>8s} {'razao':>7s}  situacao")
    over = 0
    for k, lim in LIMITS.items():
        got = actual[k]
        ratio = got / lim
        ok = got <= lim
        if not ok:
            over += 1
        print(f"{k:34s} {got:>8,} {lim:>8,} {ratio:>6.1f}x  {'cabe' if ok else 'EXCEDE'}")

    print(f"\n  tabelas: {tables} | figuras: {figures}")
    print(f"\nitens fora do limite: {over}/{len(LIMITS)}")
    raise SystemExit(1 if over else 0)


if __name__ == "__main__":
    main()
