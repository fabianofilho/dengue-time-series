"""
Combinacoes de modelos sobre as previsoes ja gravadas pelo backtest.

Nao reexecuta modelo nenhum: le results/benchmark_*_predictions.csv e combina.

A regra que decide se o resultado presta: **peso e meta-modelo so podem usar
folds estritamente anteriores ao que esta sendo previsto.** Escolher peso
olhando o backtest inteiro e o erro que faz ensemble parecer melhor do que e, e
e invisivel no numero final. Aqui a janela e expansiva, igual a do intervalo
conformal: no fold k, o combinador ve folds 0..k-1 e mais nada.

Combinacoes implementadas:

  mean      media aritmetica simples. Baseline honesto, sem parametro a estimar,
            portanto sem risco de vazamento nem de sobreajuste.
  median    mediana entre os modelos. Robusta a um membro que diverge, que e
            exatamente o caso do LightGBM e do SARIMAX em varias cidades.
  weighted  media ponderada por 1/MAE do modelo nos folds anteriores, no mesmo
            passo de horizonte.
  stacking  Ridge sobre as previsoes dos membros, ajustada nos folds anteriores.
            Padronizada, pelo mesmo motivo do ridge_forecaster.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZON = 12
MIN_TRAIN_FOLDS = 20  # mesmo aquecimento usado nos intervalos conformais
METHODS = ("mean", "median", "weighted", "stacking")


def to_wide(df: pd.DataFrame, members: list[str]) -> pd.DataFrame:
    """Uma linha por (fold, h) e uma coluna por modelo membro.

    Espera as colunas model, y_true, y_pred, fold e h, produzidas por
    dengue_forecast.intervals.add_fold_index.
    """
    missing = set(members) - set(df["model"].unique())
    if missing:
        raise ValueError(f"membros ausentes nas previsoes: {sorted(missing)}")

    wide = df.pivot_table(index=["fold", "h"], columns="model", values="y_pred")
    truth = df.pivot_table(index=["fold", "h"], columns="model", values="y_true")
    # y_true tem que ser igual entre modelos para o mesmo (fold, h)
    spread = truth.max(axis=1) - truth.min(axis=1)
    if float(spread.abs().max()) > 1e-6:
        raise ValueError("y_true diverge entre modelos no mesmo fold e horizonte")
    out = wide[members].copy()
    out["y_true"] = truth[members[0]]
    return out.reset_index()


def combine(
    wide: pd.DataFrame,
    members: list[str],
    method: str,
    min_train_folds: int = MIN_TRAIN_FOLDS,
) -> pd.Series:
    """Previsao combinada, indexada como wide. NaN durante o aquecimento.

    Para 'mean' e 'median' nao ha nada a estimar, entao poderiam cobrir todos os
    folds; ainda assim respeitam o mesmo aquecimento, para que a comparacao
    contra 'weighted' e 'stacking' seja no mesmo conjunto de linhas.
    """
    if method not in METHODS:
        raise ValueError(f"metodo desconhecido: {method}")

    out = pd.Series(np.nan, index=wide.index, dtype=float)
    X_all = wide[members].to_numpy(dtype=float)
    y_all = wide["y_true"].to_numpy(dtype=float)

    for h in range(1, HORIZON + 1):
        sel = wide.index[wide["h"] == h]
        order = wide.loc[sel].sort_values("fold").index.to_numpy()

        for pos, idx in enumerate(order):
            if pos < min_train_folds:
                continue
            past = order[:pos]  # so folds anteriores, no mesmo horizonte
            row = X_all[idx]

            if method == "mean":
                out.iloc[idx] = float(np.mean(row))
            elif method == "median":
                out.iloc[idx] = float(np.median(row))
            elif method == "weighted":
                err = np.abs(X_all[past] - y_all[past][:, None]).mean(axis=0)
                w = 1.0 / np.maximum(err, 1e-9)
                out.iloc[idx] = float(np.dot(w, row) / w.sum())
            else:  # stacking
                model = make_pipeline(StandardScaler(), Ridge())
                model.fit(X_all[past], y_all[past])
                out.iloc[idx] = float(model.predict(row.reshape(1, -1))[0])

    return out.clip(lower=0.0)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """sMAPE, MAE e RMSE, na mesma forma usada no resto do projeto."""
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    ratio = np.divide(
        np.abs(y_true - y_pred), denom, out=np.zeros_like(denom), where=denom != 0
    )
    return {
        "sMAPE": float(np.mean(ratio) * 100.0),
        "MAE": float(np.mean(np.abs(y_true - y_pred))),
        "RMSE": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
        "n": int(len(y_true)),
    }


def run_city(
    df: pd.DataFrame, members: list[str], min_train_folds: int = MIN_TRAIN_FOLDS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Avalia membros e combinacoes no MESMO conjunto de linhas.

    Comparar ensemble avaliado em 99 folds contra membro avaliado em 119 e a
    armadilha obvia, e ela favorece o ensemble se os primeiros folds forem os
    mais dificeis, que e o caso aqui: sao os de menor janela de treino.
    """
    wide = to_wide(df, members)
    preds = {m: combine(wide, members, m, min_train_folds) for m in METHODS}
    evaluated = preds["mean"].notna()
    y = wide.loc[evaluated, "y_true"].to_numpy(dtype=float)

    rows = []
    for m in members:
        r = evaluate(y, wide.loc[evaluated, m].to_numpy(dtype=float))
        rows.append({"approach": m, "kind": "member", **r})
    for name, p in preds.items():
        r = evaluate(y, p[evaluated].to_numpy(dtype=float))
        rows.append({"approach": name, "kind": "ensemble", **r})

    detail = wide.loc[evaluated, ["fold", "h", "y_true"]].copy()
    for m in members:
        detail[m] = wide.loc[evaluated, m]
    for name, p in preds.items():
        detail[f"ens_{name}"] = p[evaluated]
    return pd.DataFrame(rows), detail
