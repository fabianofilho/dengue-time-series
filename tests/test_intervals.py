"""
Testes da predicao conformal.

O teste que importa e o de cobertura: com residuo de distribuicao conhecida, o
intervalo nominal de 80% tem que cobrir perto de 80% das observacoes. Se a
implementacao estiver errada, a cobertura sai do alvo e o teste quebra.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dengue_forecast.intervals import (
    HORIZON,
    _conformal_quantile,
    add_fold_index,
    conformal_intervals,
    evaluate_intervals,
    interval_score,
    weighted_interval_score,
)


def make_backtest(n_folds=140, sigma=0.4, seed=0, growing=False):
    """Backtest sintetico: y_pred e o sinal, y_true e o sinal perturbado em log1p.

    Por construcao, log1p(y_true) - log1p(y_pred) ~ Normal(0, sigma), entao a
    cobertura teorica do intervalo conformal e o proprio nivel nominal.
    """
    rng = np.random.default_rng(seed)
    rows = []
    dates = pd.date_range("2014-01-01", periods=n_folds + HORIZON, freq="MS")
    for k in range(n_folds):
        for h in range(1, HORIZON + 1):
            base = 500 + 400 * np.sin((k + h) / 6.0)
            s = sigma * (h / 6.0) if growing else sigma
            noise = rng.normal(0, s)
            y_pred = base
            y_true = np.expm1(np.log1p(y_pred) + noise)
            rows.append(
                {
                    "model": "m",
                    "date": dates[k + h - 1],
                    "y_true": max(0.0, y_true),
                    "y_pred": y_pred,
                }
            )
    return pd.DataFrame(rows)


def test_conformal_quantile_monotonic_and_bounded():
    r = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    qs = [_conformal_quantile(r, p) for p in (0.05, 0.25, 0.5, 0.75, 0.95)]
    assert qs == sorted(qs), "quantil deve ser monotono no nivel"
    assert min(qs) >= r.min() and max(qs) <= r.max()


def test_conformal_quantile_empty():
    assert np.isnan(_conformal_quantile(np.array([]), 0.9))


def test_add_fold_index_recovers_structure():
    df = add_fold_index(make_backtest(n_folds=30))
    assert df["h"].min() == 1 and df["h"].max() == HORIZON
    assert df["fold"].nunique() == 30
    assert (df.groupby("fold")["h"].count() == HORIZON).all()


def test_add_fold_index_rejects_broken_structure():
    df = make_backtest(n_folds=10)
    df = df.drop(df.index[3]).reset_index(drop=True)  # quebra o multiplo de 12
    with pytest.raises(ValueError):
        add_fold_index(df)


@pytest.mark.parametrize("level,tol", [(0.50, 0.06), (0.80, 0.05), (0.95, 0.035)])
def test_coverage_matches_nominal(level, tol):
    """Cobertura empirica bate com o nominal em residuo de lei conhecida."""
    df = add_fold_index(make_backtest(n_folds=160, sigma=0.4, seed=7))
    out = conformal_intervals(df, levels=(level,))
    ev = evaluate_intervals(out, levels=(level,))
    cov = ev[f"coverage_{int(level * 100)}"]
    assert abs(cov - level) < tol, f"cobertura {cov:.3f} longe do nominal {level}"


def test_intervals_widen_with_horizon():
    """Com incerteza crescente em h, o intervalo tem que acompanhar."""
    df = add_fold_index(make_backtest(n_folds=160, sigma=0.35, seed=3, growing=True))
    out = conformal_intervals(df, levels=(0.80,))
    w = (out["hi_80"] - out["lo_80"]).groupby(out["h"]).median().dropna()
    assert w.loc[12] > w.loc[1] * 2, "intervalo em h=12 deveria ser bem maior que em h=1"


def test_no_interval_before_warmup():
    df = add_fold_index(make_backtest(n_folds=40))
    out = conformal_intervals(df, levels=(0.80,), min_calib_folds=20)
    early = out[out["fold"] < 20]
    late = out[out["fold"] >= 20]
    assert early["lo_80"].isna().all(), "fold em aquecimento nao pode ter intervalo"
    assert late["lo_80"].notna().all(), "fold apos aquecimento tem que ter intervalo"


def test_calibration_uses_only_past_folds():
    """Alterar um fold futuro nao pode mudar o intervalo de um fold anterior."""
    df = add_fold_index(make_backtest(n_folds=60, seed=11))
    a = conformal_intervals(df, levels=(0.80,))
    tampered = df.copy()
    last = tampered["fold"] == tampered["fold"].max()
    tampered.loc[last, "y_true"] = tampered.loc[last, "y_true"] * 50
    b = conformal_intervals(tampered, levels=(0.80,))
    earlier = a["fold"] < a["fold"].max()
    pd.testing.assert_series_equal(a.loc[earlier, "lo_80"], b.loc[earlier, "lo_80"])


def test_interval_score_penalises_miss():
    lo, hi = np.array([10.0]), np.array([20.0])
    inside = interval_score(np.array([15.0]), lo, hi, 0.2)
    outside = interval_score(np.array([40.0]), lo, hi, 0.2)
    assert inside[0] == pytest.approx(10.0), "dentro do intervalo, escore e a largura"
    assert outside[0] > inside[0]


def test_wis_prefers_the_better_forecast():
    y = np.array([100.0])
    tight_right = {0.8: (np.array([90.0]), np.array([110.0]))}
    wide = {0.8: (np.array([10.0]), np.array([300.0]))}
    tight_wrong = {0.8: (np.array([300.0]), np.array([320.0]))}
    a = weighted_interval_score(y, tight_right, np.array([100.0]))[0]
    b = weighted_interval_score(y, wide, np.array([100.0]))[0]
    c = weighted_interval_score(y, tight_wrong, np.array([310.0]))[0]
    assert a < b < c, "WIS deve premiar nitidez com cobertura e punir viés"


@pytest.mark.parametrize("scale", ["log1p", "absolute"])
def test_coverage_holds_in_both_scales(scale):
    """A cobertura tem que bater com o nominal nas duas construcoes."""
    if scale == "log1p":
        df = add_fold_index(make_backtest(n_folds=160, sigma=0.4, seed=5))
    else:
        # residuo aditivo de lei conhecida, que e o caso que 'absolute' modela
        rng = np.random.default_rng(5)
        rows = []
        dates = pd.date_range("2014-01-01", periods=160 + HORIZON, freq="MS")
        for k in range(160):
            for h in range(1, HORIZON + 1):
                base = 5000 + 1000 * np.sin((k + h) / 6.0)
                rows.append({"model": "m", "date": dates[k + h - 1],
                             "y_true": base + rng.normal(0, 300), "y_pred": base})
        df = add_fold_index(pd.DataFrame(rows))
    out = conformal_intervals(df, levels=(0.80,), scale=scale)
    cov = evaluate_intervals(out, levels=(0.80,))["coverage_80"]
    assert abs(cov - 0.80) < 0.05, f"{scale}: cobertura {cov:.3f}"


def test_unknown_scale_rejected():
    df = add_fold_index(make_backtest(n_folds=30))
    with pytest.raises(ValueError):
        conformal_intervals(df, scale="sqrt")
