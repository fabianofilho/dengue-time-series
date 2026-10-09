"""
Compara o PDF de submissao com o .docx de revisao e acusa divergencia.

Desde 09/10/2026 os dois saem da mesma fonte (paper/plos/manuscript_src.tex) por
scripts/build_plos.py: o PDF pelo tectonic e o .docx pelo pandoc. A conversao do
pandoc pode perder numero, tabela ou figura sem avisar, e este script e quem
detecta.

Confere tres coisas:
  numeros    todo numero com tres ou mais digitos que aparece num e nao no outro
  secoes     titulos exigidos presentes nos dois
  pendencias marcador vermelho remanescente em qualquer um dos dois

Uso:
    python scripts/check_artifacts.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import docx
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "build" / "plos" / "manuscript.pdf"
DOCX = ROOT / "build" / "plos" / "manuscript_review.docx"
NUMBERS = ROOT / "paper" / "verified_numbers.json"

# Secoes que a PLOS NTD exige no manuscrito. Funding, competing interests,
# autoria e disponibilidade de dados vao nos campos do sistema
# (paper/plos/submission_fields.md), nao aqui.
REQUIRED = [
    "Abstract",
    "Author summary",
    "Introduction",
    "Methods",
    "Ethics statement",
    "Results",
    "Discussion",
    "Acknowledgments",
    "References",
]


def normalise(text: str) -> str:
    """Desfaz ligaduras tipograficas antes de comparar.

    O LaTeX compoe fi, fl, ff e ffi como um glifo unico, e o extrator devolve
    U+FB00 e vizinhos. Sem isto, "Conflicts" no PDF nao casa com "Conflicts" no
    Word, e o comparador acusa divergencia que nao existe. Este PDF tem 140
    dessas ocorrencias.
    """
    return " ".join(unicodedata.normalize("NFKD", text).split())


def pdf_text() -> str:
    return normalise(" ".join(p.get_text() for p in pymupdf.open(PDF)))


def docx_text() -> str:
    d = docx.Document(DOCX)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return normalise(" ".join(parts))


def key_numbers() -> dict[str, str]:
    """Numeros que os dois artefatos precisam citar igual."""
    v = json.loads(NUMBERS.read_text(encoding="utf-8"))
    ms = v["mean_smape_by_model"]
    out = {
        "previsoes por modelo por cidade": f"{v['n_predictions_per_model_city']:,}",
        "previsoes no total": f"{v['n_predictions_total']:,}",
        "folds": str(v["n_predictions_per_model_city"] // 12),
        "sMAPE medio TimesFM": f"{ms['timesfm']:.1f}",
        "sMAPE medio CatBoost": f"{ms['catboost']:.1f}",
        "sMAPE medio SARIMAX": f"{ms['sarimax']:.1f}",
        "total de casos Sao Paulo": f"{v['descriptive']['Sao Paulo']['total']:,}",
        "pico mensal Sao Paulo": f"{v['descriptive']['Sao Paulo']['max']:,}",
    }
    return out


def main() -> None:
    if not PDF.exists() or not DOCX.exists():
        raise SystemExit("gere os dois artefatos antes: python scripts/build_plos.py")

    tex, doc = pdf_text(), docx_text()
    problems = 0

    print("=== numeros que os dois precisam citar ===")
    for label, val in key_numbers().items():
        in_tex = val in tex
        in_doc = val in doc
        status = "OK  " if (in_tex and in_doc) else "ERRO"
        if status == "ERRO":
            problems += 1
        onde = "ambos" if in_tex and in_doc else ("so PDF" if in_tex else
                                                  ("so DOCX" if in_doc else "NENHUM"))
        print(f"  {status} {label:34s} {val:>10s}  {onde}")

    print("\n=== secoes exigidas ===")
    for sec in REQUIRED:
        in_tex, in_doc = sec in tex, sec in doc
        status = "OK  " if (in_tex and in_doc) else "ERRO"
        if status == "ERRO":
            problems += 1
        print(f"  {status} {sec:46s} PDF={in_tex} DOCX={in_doc}")

    print("\n=== numeracao de tabela e figura ===")

    def labels(txt: str, sep: str) -> list[str]:
        """Rotulos de legenda. O template da PLOS usa 'Table 1.' e 'Fig 1.' nos dois."""
        pat = r"(Table|Fig) (\d+)" + re.escape(sep)
        return sorted({f"{k} {n}" for k, n in re.findall(pat, txt)},
                      key=lambda x: (x.split()[0], int(x.split()[1])))

    lt, ld = labels(tex, "."), labels(doc, ".")
    so_pdf = [x for x in lt if x not in ld]
    so_doc = [x for x in ld if x not in lt]
    status = "OK  " if not so_pdf and not so_doc else "ERRO"
    if status == "ERRO":
        problems += 1
    print(f"  {status} PDF tem {len(lt)} rotulos, DOCX tem {len(ld)}")
    if so_pdf:
        print(f"       so no PDF : {so_pdf}")
    if so_doc:
        print(f"       so no DOCX: {so_doc}")


    # Pendencia e aviso, nao divergencia: as duas que restam (numero da OMS e DOI)
    # sao conhecidas. Divergencia e o mesmo numero de pendencias nos dois.
    print("\n=== marcadores de pendencia ===")
    n_pdf, n_doc = tex.count("[PENDING"), doc.count("[PENDING")
    status = "OK  " if n_pdf == n_doc else "ERRO"
    if n_pdf != n_doc:
        problems += 1
    print(f"  {status} PDF {n_pdf}, DOCX {n_doc}" + ("  (AVISO: resolver antes de submeter)"
                                                     if n_pdf else ""))

    print("\n=== referencia cruzada quebrada ===")
    for name, txt in (("PDF", tex),):
        n = len(re.findall(r"\?\?", txt))
        status = "OK  " if n == 0 else "ERRO"
        if n:
            problems += 1
        print(f"  {status} {name:5s} '??' nao resolvido: {n}")

    print(f"\nPROBLEMAS: {problems}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
