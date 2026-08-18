"""
Calcula intervalos de predicao conformais sobre as previsoes ja gravadas pelo
backtest, nas duas construcoes (log1p e absoluta), e avalia cobertura e WIS.

Nao reexecuta modelo nenhum: le results/benchmark_*_predictions.csv.

Saidas:
  results/comparisons/predictions_with_intervals.csv
  results/comparisons/interval_calibration.csv

Uso:
    PYTHONPATH=src python scripts/run_intervals.py
"""
from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

from dengue_forecast.intervals import (
    MIN_CALIB_FOLDS,
    add_fold_index,
    conformal_intervals,
    evaluate_intervals,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "comparisons"
SCALES = ("log1p", "absolute")


def main() -> None:
    cal_rows, frames = [], []
    for f in sorted(glob.glob(str(ROOT / "results" / "benchmark_*_predictions.csv"))):
        city = Path(f).name.replace("benchmark_", "").replace("_predictions.csv", "")
        base = add_fold_index(pd.read_csv(f))
        for scale in SCALES:
            d = conformal_intervals(base.copy(), scale=scale)
            d.insert(0, "city", city)
            d["scale"] = scale
            frames.append(d)
            for model, sub in d.groupby("model"):
                ev = evaluate_intervals(sub)
                ev.update(city=city, model=model, scale=scale)
                cal_rows.append(ev)
        print(f"  {city:16s} ok")

    OUT.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_csv(
        OUT / "predictions_with_intervals.csv", index=False
    )
    cal = pd.DataFrame(cal_rows)
    cal.to_csv(OUT / "interval_calibration.csv", index=False)

    print(f"\naquecimento: {MIN_CALIB_FOLDS} folds sem intervalo")
    print(f"previsoes avaliadas por modelo por cidade: {cal['n_evaluated'].iloc[0]}")
    print("\ncobertura media entre as 8 cidades (nominal 50 / 80 / 95):")
    for scale in SCALES:
        c = cal[cal["scale"] == scale]
        g = c.groupby("model")[["coverage_50", "coverage_80", "coverage_95"]].mean() * 100
        print(f"  -- {scale}")
        for m in g.index:
            print(
                f"     {m:14s} {g.loc[m, 'coverage_50']:5.1f} "
                f"{g.loc[m, 'coverage_80']:5.1f} {g.loc[m, 'coverage_95']:5.1f}"
            )


if __name__ == "__main__":
    main()
