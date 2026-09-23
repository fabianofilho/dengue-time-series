"""
Avalia combinacoes de modelos nas 8 cidades, sobre as previsoes ja gravadas.

Nao reexecuta modelo nenhum. Peso e meta-modelo usam apenas folds anteriores ao
que esta sendo previsto, com janela expansiva, pelo mesmo motivo que o backtest
nao treina em dados futuros.

Saidas:
  results/comparisons/ensemble_summary.csv    metricas por cidade e abordagem
  results/comparisons/ensemble_predictions.csv previsoes membro a membro

O conjunto de membros muda o resultado de toda abordagem, inclusive das que
nao estimam nada: a mediana de 7 previsoes nao e a mediana de 12. Por isso o
conjunto e um argumento explicito e cada variante escreve no proprio arquivo,
em vez de a saida depender de quais modelos por acaso estao no CSV.

Uso:
    PYTHONPATH=src python scripts/run_ensembles.py
    PYTHONPATH=src python scripts/run_ensembles.py --members publicados,globais \
        --out-suffix _with_global
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import pandas as pd

from dengue_forecast.ensembles import METHODS, MIN_TRAIN_FOLDS, run_city
from dengue_forecast.intervals import add_fold_index

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "comparisons"

# Todos os sete, incluindo os ruins. Descartar membro fraco olhando o resultado
# do proprio backtest seria selecionar com a mesma informacao usada para avaliar.
# Pela mesma razao, quando os globais entram, entram todos os cinco.
PUBLICADOS = ["timesfm", "catboost", "xgboost", "randomforest", "sarimax", "ridge", "lgbm"]
GLOBAIS = [
    "global_lgbm",
    "global_xgboost",
    "global_catboost",
    "global_randomforest",
    "global_ridge",
]
GRUPOS = {"publicados": PUBLICADOS, "globais": GLOBAIS}

# O naive sazonal fica de fora de proposito. Ele e a referencia contra a qual o
# ensemble e julgado, e nao da para ser regua e competidor no mesmo numero.
MEMBERS = PUBLICADOS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--members",
        default="publicados",
        help=(
            "Grupos (publicados, globais) ou nomes de modelo, separados por virgula. "
            "O default reproduz o conjunto do artigo."
        ),
    )
    p.add_argument(
        "--out-suffix",
        default="",
        help="Sufixo dos arquivos de saida. Use para nao sobrescrever a variante publicada.",
    )
    return p.parse_args()


def resolve_members(spec: str) -> list[str]:
    membros: list[str] = []
    for item in (x.strip() for x in spec.split(",") if x.strip()):
        membros.extend(GRUPOS.get(item, [item]))
    vistos = set()
    saida = [m for m in membros if not (m in vistos or vistos.add(m))]
    if len(saida) < 2:
        raise ValueError(f"Ensemble precisa de ao menos 2 membros, recebeu {saida}")
    return saida


def main() -> None:
    args = parse_args()
    members = resolve_members(args.members)
    suffix = args.out_suffix
    print(f"[INFO] {len(members)} membros: {', '.join(members)}")

    summaries, details = [], []
    for f in sorted(glob.glob(str(ROOT / "results" / "benchmark_*_predictions.csv"))):
        city = Path(f).name.replace("benchmark_", "").replace("_predictions.csv", "")
        df = add_fold_index(pd.read_csv(f))
        faltando = sorted(set(members) - set(df["model"].unique()))
        if faltando:
            raise ValueError(f"{city}: membros ausentes no CSV: {faltando}")
        s, d = run_city(df, members, min_train_folds=MIN_TRAIN_FOLDS)
        s.insert(0, "city", city)
        d.insert(0, "city", city)
        summaries.append(s)
        details.append(d)
        best = s.loc[s["sMAPE"].idxmin()]
        print(f"  {city:16s} melhor: {best['approach']:14s} sMAPE {best['sMAPE']:6.2f} "
              f"({best['kind']})")

    summary = pd.concat(summaries, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / f"ensemble_summary{suffix}.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(
        OUT / f"ensemble_predictions{suffix}.csv", index=False
    )

    print(f"\naquecimento: {MIN_TRAIN_FOLDS} folds; avaliadas "
          f"{summary['n'].iloc[0]:,} previsoes por abordagem por cidade")

    print("\nmedia entre as 8 cidades:")
    g = summary.groupby(["kind", "approach"])[["sMAPE", "MAE", "RMSE"]].mean()
    g = g.sort_values("sMAPE")
    for (kind, name), r in g.iterrows():
        tag = "ENSEMBLE" if kind == "ensemble" else "        "
        print(f"  {tag} {name:14s} sMAPE {r['sMAPE']:7.2f}  MAE {r['MAE']:10.1f}  "
              f"RMSE {r['RMSE']:11.1f}")

    print("\nvitorias por cidade (menor sMAPE):")
    wins = summary.loc[summary.groupby("city")["sMAPE"].idxmin()]
    for name, n in wins["approach"].value_counts().items():
        print(f"  {name:14s} {n}/8")

    print("\no ensemble bate o melhor membro da propria cidade?")
    for city, sub in summary.groupby("city"):
        mem = sub[sub["kind"] == "member"]["sMAPE"].min()
        ens = sub[sub["kind"] == "ensemble"]["sMAPE"].min()
        delta = mem - ens
        verdict = "sim" if delta > 0 else "nao"
        print(f"  {city:16s} melhor membro {mem:6.2f} | melhor ensemble {ens:6.2f} "
              f"| {verdict} ({delta:+.2f})")


if __name__ == "__main__":
    main()
