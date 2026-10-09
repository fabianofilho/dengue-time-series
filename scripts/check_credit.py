"""
Audita a declaracao CRediT da submissao (paper/plos/submission_fields.md).

Na PLOS a autoria vai no campo do sistema, nao no manuscrito, entao a declaracao
mora no arquivo dos campos prontos para colar.

Confere os 14 papeis da taxonomia, a ordem alfabetica dentro de cada autor, a
contradicao entre Funding acquisition e a declaracao de ausencia de
financiamento, e o criterio do ICMJE que um autor nao cumpre so revisando.

Uso:
    python scripts/check_credit.py
"""
import io
import re

CREDIT = {
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition",
    "Investigation", "Methodology", "Project administration", "Resources", "Software",
    "Supervision", "Validation", "Visualization",
    "Writing: original draft", "Writing: review and editing",
}

s = io.open("paper/plos/submission_fields.md", encoding="utf-8").read()
blk = s[s.index("Author Contributions"): s.index("All authors read")]

authors = re.findall(r"\*\*([^*\n]+):\*\* ([^\n]*)", blk)
bad = 0
for name, roles in authors:
    ps = [p.strip().rstrip(".") for p in roles.split(",") if p.strip()]
    unknown = [p for p in ps if p not in CREDIT]
    alpha = ps == sorted(ps)
    print(f"{name:26s} {len(ps):2d} papeis | alfabetico: {'sim' if alpha else 'NAO'} "
          f"| fora da taxonomia: {unknown or 'nenhum'}")
    if unknown or not alpha:
        bad += 1
    if ps == ["Writing: review and editing"]:
        print("   AVISO ICMJE: contribuicao so de revisao")
        bad += 1

print()
funding = "Funding acquisition" in blk
nofund = "received no specific funding" in s
print(f"Funding acquisition declarado: {funding} | artigo nega financiamento: {nofund}")
if funding and nofund:
    print("   CONTRADICAO: Funding acquisition com financiamento negado")
    bad += 1
if "Writing: original draft" not in blk:
    print("   AVISO: ninguem declarou ter escrito o rascunho")
    bad += 1
print(f"\nPROBLEMAS: {bad}")
