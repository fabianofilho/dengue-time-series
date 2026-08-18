"""
Avalia combinacoes de modelos nas 8 cidades, sobre as previsoes ja gravadas.

Nao reexecuta modelo nenhum. Peso e meta-modelo usam apenas folds anteriores ao
que esta sendo previsto, com janela expansiva, pelo mesmo motivo que o backtest
nao treina em dados futuros.

Saidas:
  results/comparisons/ensemble_summary.csv    metricas por cidade e abordagem
  results/comparisons/ensemble_predictions.csv previsoes membro a membro

Uso:
    PYTHONPATH=src python scripts/run_ensembles.py
"""
from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

from dengue_forecast.ensembles import METHODS, MIN_TRAIN_FOLDS, run_city
from dengue_forecast.intervals import add_fold_index

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "comparisons"

# Todos os sete, incluindo os ruins. Descartar membro fraco olhando o resultado
# do proprio backtest seria selecionar com a mesma informacao usada para avaliar.
MEMBERS = ["timesfm", "catboost", "xgboost", "randomforest", "sarimax", "ridge", "lgbm"]


def main() -> None:
    summaries, details = [], []
    for f in sorted(glob.glob(str(ROOT / "results" / "benchmark_*_predictions.csv"))):
        city = Path(f).name.replace("benchmark_", "").replace("_predictions.csv", "")
        df = add_fold_index(pd.read_csv(f))
        s, d = run_city(df, MEMBERS, min_train_folds=MIN_TRAIN_FOLDS)
        s.insert(0, "city", city)
        d.insert(0, "city", city)
        summaries.append(s)
        details.append(d)
        best = s.loc[s["sMAPE"].idxmin()]
        print(f"  {city:16s} melhor: {best['approach']:14s} sMAPE {best['sMAPE']:6.2f} "
              f"({best['kind']})")

    summary = pd.concat(summaries, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "ensemble_summary.csv", index=False)
    pd.concat(details, ignore_index=True).to_csv(
        OUT / "ensemble_predictions.csv", index=False
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
