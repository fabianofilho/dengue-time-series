"""
Baixa do IBGE os dois insumos que faltam para a analise de clusters:
populacao anual por municipio (denominador) e centroide (lat/lon).

Fontes, todas via API publica do IBGE:
  - Censo 2010  : SIDRA tabela 1378, variavel 93 (populacao residente)
  - Estimativas : SIDRA tabela 6579, variavel 9324 (populacao estimada)
  - Censo 2022  : SIDRA tabela 4709, variavel 93
  - Centroides  : malha municipal, /api/v3/malhas (GeoJSON), centroide do poligono

Anos sem publicacao (2007 e 2010 nas estimativas, e 2024) sao preenchidos por
interpolacao linear entre os anos observados, e o metodo fica registrado na
coluna 'source' de cada linha. Nada e inventado em silencio.

Uso:
    python scripts/fetch_ibge.py
"""
from __future__ import annotations

import gzip
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

CITIES = {
    "Sao Paulo": 3550308,
    "Rio de Janeiro": 3304557,
    "Belo Horizonte": 3106200,
    "Brasilia": 5300108,
    "Fortaleza": 2304400,
    "Recife": 2611606,
    "Manaus": 1302603,
    "Salvador": 2927408,
}

YEARS = list(range(2010, 2025))


def get(url: str):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    raw = urllib.request.urlopen(req, timeout=240).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def sidra(table: int, var: int, code: int, period: str) -> dict[int, int]:
    """Retorna {ano: populacao} de uma tabela do SIDRA."""
    url = f"https://apisidra.ibge.gov.br/values/t/{table}/n6/{code}/v/{var}/p/{period}"
    out = {}
    for row in get(url)[1:]:  # linha 0 e o cabecalho descritivo
        v = row.get("V")
        if v in (None, "-", "...", "..", "X"):
            continue
        out[int(row["D3C"])] = int(float(v))
    return out


def population(code: int) -> dict[int, tuple[int, str]]:
    """Serie anual 2010 a 2024 ancorada nos dois censos, com a origem de cada valor.

    Por que nao usar a tabela de estimativas diretamente: ela mistura dois
    regimes incompativeis. Ate 2021 traz a projecao anterior ao Censo 2022, que
    o censo revisou fortemente para baixo (de -7.6% em Sao Paulo a -16.6% em
    Salvador). Concatenar os dois produz um degrau artificial em 2022 em todas
    as cidades, e um scan de Poisson leria esse degrau como cluster de alta
    incidencia em toda cidade a partir de 2022, sem nenhuma relacao com dengue.

    A serie usada aqui ancora nas duas enumeracoes de fato, os Censos 2010 e
    2022, e interpola geometricamente entre elas (taxa de crescimento anual
    constante, pratica demografica padrao para estimativa intercensitaria).
    2023 e 2024 seguem extrapolados pela mesma taxa intercensitaria, e nao
    pelas estimativas pos-censo, para manter a serie internamente coerente.
    """
    c2010 = sidra(1378, 93, code, "2010")[2010]
    c2022 = sidra(4709, 93, code, "2022")[2022]

    # taxa geometrica anual entre os dois censos
    rate = (c2022 / c2010) ** (1 / (2022 - 2010))

    full: dict[int, tuple[int, str]] = {}
    for y in YEARS:
        if y == 2010:
            full[y] = (c2010, "Censo 2010 (SIDRA 1378), enumeracao")
        elif y == 2022:
            full[y] = (c2022, "Censo 2022 (SIDRA 4709), enumeracao")
        elif y < 2022:
            full[y] = (
                round(c2010 * rate ** (y - 2010)),
                f"interpolacao geometrica intercensitaria ({rate:.5f}/ano)",
            )
        else:
            full[y] = (
                round(c2022 * rate ** (y - 2022)),
                f"extrapolacao geometrica pos-censo ({rate:.5f}/ano)",
            )
    return full


def centroid(code: int) -> tuple[float, float]:
    """Centroide simples do poligono municipal, media dos vertices do anel externo.

    Suficiente para o scan espaco-temporal, que usa a distancia entre cidades
    separadas por centenas de quilometros. Nao e centroide de area ponderado.
    """
    gj = get(f"https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}?formato=application/vnd.geo+json")
    xs, ys = [], []

    def walk(coords):
        if isinstance(coords[0], (int, float)):
            xs.append(coords[0])
            ys.append(coords[1])
        else:
            for c in coords:
                walk(c)

    for feat in gj["features"]:
        walk(feat["geometry"]["coordinates"])
    return round(sum(ys) / len(ys), 6), round(sum(xs) / len(xs), 6)


def main() -> None:
    pop_rows, geo_rows = [], []
    for name, code in CITIES.items():
        pop = population(code)
        lat, lon = centroid(code)
        geo_rows.append({"city": name, "ibge_code": code, "lat": lat, "lon": lon})
        for year, (val, src) in sorted(pop.items()):
            pop_rows.append(
                {"city": name, "ibge_code": code, "year": year, "population": val, "source": src}
            )
        print(
            f"{name:16s} {code}  lat={lat:9.4f} lon={lon:9.4f}  "
            f"pop 2010={pop[2010][0]:>9,}  pop 2024={pop[2024][0]:>9,}"
        )

    import csv

    with open(OUT / "ibge_population.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pop_rows[0]))
        w.writeheader()
        w.writerows(pop_rows)
    with open(OUT / "ibge_centroids.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(geo_rows[0]))
        w.writeheader()
        w.writerows(geo_rows)

    print(f"\nescrito data/raw/ibge_population.csv ({len(pop_rows)} linhas)")
    print(f"escrito data/raw/ibge_centroids.csv ({len(geo_rows)} linhas)")
    srcs = {}
    for r in pop_rows:
        srcs[r["source"]] = srcs.get(r["source"], 0) + 1
    print("\norigem dos valores de populacao:")
    for s, n in sorted(srcs.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {s}")

    # Quanto o Censo 2022 revisou a projecao anterior. Este e o numero citado nos
    # Methods para justificar nao usar a serie de estimativas publicada.
    print("\nrevisao do Censo 2022 contra a projecao de 2021 (motivo de nao usar 6579):")
    revs = []
    for name, code in CITIES.items():
        proj2021 = sidra(6579, 9324, code, "2021")[2021]
        c2022 = sidra(4709, 93, code, "2022")[2022]
        pct = 100 * (c2022 - proj2021) / proj2021
        revs.append((pct, name))
        print(f"  {name:16s} projecao 2021 {proj2021:>10,} -> censo 2022 {c2022:>10,}  {pct:+6.2f}%")
    revs.sort()
    print(f"  faixa: {revs[-1][1]} {revs[-1][0]:+.1f}% a {revs[0][1]} {revs[0][0]:+.1f}%")


if __name__ == "__main__":
    main()
