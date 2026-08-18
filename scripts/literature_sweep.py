"""
Varredura dirigida da literatura de previsao de dengue em 2025 e 2026.

Nao e revisao sistematica. E uma checagem de cobertura: encontrar o que o
manuscrito precisaria citar e nao cita, antes que um revisor encontre.

Quatro frentes, escolhidas porque cada uma poderia derrubar uma afirmacao
diferente do artigo:
  brasil       concorrente direto, ameaca o ineditismo
  foundation   ameaca a afirmacao de que nao avaliaram foundation model em dengue
  probabilist  ameaca a contribuicao de intervalo e calibracao
  benchmark    ameaca a afirmacao de que falta benchmark padronizado

Uso:
    python scripts/literature_sweep.py [--rows 25]
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "literature_sweep.json"
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
YEARS = "(PUB_YEAR:2025 OR PUB_YEAR:2026)"

QUERIES = {
    "brasil": (
        'TITLE_ABS:"dengue" AND TITLE_ABS:(forecast* OR predict* OR "early warning") '
        f'AND TITLE_ABS:(brazil* OR brasil* OR infodengue) AND {YEARS}'
    ),
    "foundation": (
        'TITLE_ABS:(dengue OR arbovirus OR epidemic OR influenza OR "infectious disease") '
        'AND TITLE_ABS:("foundation model" OR "zero-shot" OR "TimesFM" OR "Chronos" OR '
        f'"time series foundation") AND {YEARS}'
    ),
    "probabilistic": (
        'TITLE_ABS:"dengue" AND TITLE_ABS:(forecast* OR predict*) '
        'AND TITLE_ABS:("prediction interval" OR "weighted interval score" OR conformal '
        f'OR calibration OR probabilistic OR uncertainty) AND {YEARS}'
    ),
    "benchmark": (
        'TITLE_ABS:"dengue" AND TITLE_ABS:(forecast* OR predict*) '
        'AND TITLE_ABS:(benchmark OR "model comparison" OR comparative OR '
        f'"multi-city" OR "machine learning") AND {YEARS}'
    ),
}


# ja citados no manuscrito, por DOI, para nao aparecerem como lacuna
def cited_dois() -> set[str]:
    bib = (ROOT / "paper" / "refs" / "references.bib").read_text(encoding="utf-8")
    return {d.lower() for d in re.findall(r"doi\s*=\s*\{([^}]+)\}", bib)}


def search(query: str, rows: int) -> list[dict]:
    url = (
        f"{API}?query={urllib.parse.quote(query)}&format=json"
        f"&pageSize={rows}&sort=P_PDATE_D%20desc"
    )
    with urllib.request.urlopen(url, timeout=180) as r:
        data = json.load(r)
    out = []
    for x in data.get("resultList", {}).get("result", []):
        out.append({
            "title": " ".join((x.get("title") or "").split()),
            "journal": x.get("journalTitle") or x.get("bookOrReportDetails", {}).get("publisher", ""),
            "year": x.get("pubYear"),
            "doi": (x.get("doi") or "").lower(),
            "cited": int(x.get("citedByCount") or 0),
            "type": x.get("pubType", ""),
            "id": x.get("id"),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=25)
    args = ap.parse_args()

    known = cited_dois()
    seen: dict[str, dict] = {}
    for facet, q in QUERIES.items():
        hits = search(q, args.rows)
        print(f"{facet:14s} {len(hits):3d} resultados")
        for h in hits:
            key = h["doi"] or h["title"][:70].lower()
            if key in seen:
                seen[key]["facets"].append(facet)
            else:
                h["facets"] = [facet]
                h["already_cited"] = h["doi"] in known if h["doi"] else False
                seen[key] = h

    rows = sorted(seen.values(), key=lambda r: (-len(r["facets"]), -int(r["year"] or 0), -r["cited"]))
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    novos = [r for r in rows if not r["already_cited"]]
    print(f"\n{len(rows)} unicos, {len(rows) - len(novos)} ja citados, {len(novos)} novos")
    print(f"escrito {OUT.relative_to(ROOT)}\n")

    print("mais relevantes ainda nao citados (por numero de frentes, depois ano):")
    for r in novos[:22]:
        f = ",".join(r["facets"])
        print(f"  [{f:28s}] {r['year']} {r['cited']:>4d}cit  {r['title'][:78]}")
        print(f"        {r['journal'][:60]:62s} {r['doi']}")


if __name__ == "__main__":
    main()
