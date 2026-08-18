"""
Testes das combinacoes de modelos.

O teste que importa e o de vazamento: adulterar um fold futuro nao pode mudar a
previsao combinada de um fold anterior. Um ensemble com peso escolhido no
backtest inteiro passa em todos os outros testes e falha neste.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dengue_forecast.ensembles import (
    HORIZON,
    METHODS,
    combine,
    evaluate,
    run_city,
    to_wide,
)

MEMBERS = ["a", "b", "c"]


def make_preds(n_folds=60, seed=0, biases=(0.0, 0.0, 0.0), noises=(50.0, 50.0, 50.0)):
    """Tres modelos sinteticos sobre a mesma verdade, com vies e ruido dados."""
    rng = np.random.default_rng(seed)
    rows = []
    dates = pd.date_range("2014-01-01", periods=n_folds + HORIZON, freq="MS")
    for k in range(n_folds):
        for h in range(1, HORIZON + 1):
            truth = 1000 + 400 * np.sin((k + h) / 6.0)
            for name, bias, noise in zip(MEMBERS, biases, noises):
                rows.append({
                    "model": name,
                    "date": dates[k + h - 1],
                    "y_true": truth,
                    "y_pred": max(0.0, truth + bias + rng.normal(0, noise)),
                    "fold": k,
                    "h": h,
                })
    return pd.DataFrame(rows)


def test_to_wide_shape_and_truth():
    w = to_wide(make_preds(n_folds=30), MEMBERS)
    assert len(w) == 30 * HORIZON
    assert set(MEMBERS) <= set(w.columns)
    assert w["y_true"].notna().all()


def test_to_wide_rejects_missing_member():
    with pytest.raises(ValueError, match="membros ausentes"):
        to_wide(make_preds(n_folds=10), MEMBERS + ["inexistente"])


def test_to_wide_rejects_inconsistent_truth():
    df = make_preds(n_folds=10)
    df.loc[(df.model == "a") & (df.fold == 3) & (df.h == 1), "y_true"] = 99999
    with pytest.raises(ValueError, match="y_true diverge"):
        to_wide(df, MEMBERS)


@pytest.mark.parametrize("method", METHODS)
def test_warmup_is_respected(method):
    w = to_wide(make_preds(n_folds=40), MEMBERS)
    p = combine(w, MEMBERS, method, min_train_folds=20)
    assert p[w["fold"] < 20].isna().all(), "fold em aquecimento nao pode ter combinacao"
    assert p[w["fold"] >= 20].notna().all()


def test_unknown_method_rejected():
    w = to_wide(make_preds(n_folds=30), MEMBERS)
    with pytest.raises(ValueError, match="metodo desconhecido"):
        combine(w, MEMBERS, "bagging")


def test_mean_is_the_arithmetic_mean():
    w = to_wide(make_preds(n_folds=30), MEMBERS)
    p = combine(w, MEMBERS, "mean", min_train_folds=20)
    ok = p.notna()
    assert np.allclose(p[ok], w.loc[ok, MEMBERS].mean(axis=1), atol=1e-9)


@pytest.mark.parametrize("method", METHODS)
def test_no_leakage_from_future_folds(method):
    """Adulterar o ultimo fold nao pode mudar combinacao de fold anterior."""
    df = make_preds(n_folds=45, seed=3)
    a = combine(to_wide(df, MEMBERS), MEMBERS, method, min_train_folds=20)

    tampered = df.copy()
    last = tampered["fold"] == tampered["fold"].max()
    tampered.loc[last, "y_pred"] *= 100
    tampered.loc[last, "y_true"] *= 100
    b = combine(to_wide(tampered, MEMBERS), MEMBERS, method, min_train_folds=20)

    w = to_wide(df, MEMBERS)
    earlier = (w["fold"] < w["fold"].max()).to_numpy()
    np.testing.assert_allclose(
        a[earlier].dropna().to_numpy(), b[earlier].dropna().to_numpy(), rtol=1e-9
    )


def test_weighted_favours_the_accurate_member():
    """Com um membro muito melhor, o peso tem que puxar a combinacao para ele."""
    df = make_preds(n_folds=60, seed=5, noises=(5.0, 400.0, 400.0))
    w = to_wide(df, MEMBERS)
    wt = combine(w, MEMBERS, "weighted", min_train_folds=20)
    mn = combine(w, MEMBERS, "mean", min_train_folds=20)
    ok = wt.notna()
    y = w.loc[ok, "y_true"].to_numpy()
    err_w = np.abs(wt[ok].to_numpy() - y).mean()
    err_m = np.abs(mn[ok].to_numpy() - y).mean()
    assert err_w < err_m, "ponderada deveria bater a media simples aqui"


def test_median_resists_a_diverging_member():
    """Um membro que explode nao pode arrastar a mediana como arrasta a media."""
    df = make_preds(n_folds=50, seed=7)
    df.loc[df.model == "c", "y_pred"] *= 60  # membro c vira lixo
    w = to_wide(df, MEMBERS)
    y = w["y_true"].to_numpy()
    md = combine(w, MEMBERS, "median", min_train_folds=20)
    mn = combine(w, MEMBERS, "mean", min_train_folds=20)
    ok = md.notna().to_numpy()
    assert np.abs(md[ok] - y[ok]).mean() < np.abs(mn[ok] - y[ok]).mean()


def test_run_city_evaluates_everyone_on_the_same_rows():
    """Membro e ensemble tem que ser avaliados no mesmo n, senao a comparacao mente."""
    df = make_preds(n_folds=50, seed=11)
    summary, detail = run_city(df, MEMBERS, min_train_folds=20)
    assert summary["n"].nunique() == 1, "n diferente entre abordagens invalida a comparacao"
    assert len(detail) == summary["n"].iloc[0]
    assert set(summary["kind"]) == {"member", "ensemble"}


def test_evaluate_perfect_forecast():
    y = np.array([10.0, 20.0, 30.0])
    r = evaluate(y, y.copy())
    assert r["MAE"] == 0 and r["RMSE"] == 0 and r["sMAPE"] == 0
