"""
Intervalos de predicao conformais para o backtest de origem rolante.

Ideia: a previsao pontual de cada modelo ja existe. O intervalo sai da
distribuicao empirica dos erros que aquele modelo cometeu, no mesmo passo de
horizonte, em folds ANTERIORES ao que esta sendo previsto. Nenhum residuo do
proprio fold nem de folds futuros entra na calibracao, pelo mesmo motivo que o
backtest nao treina em dados futuros.

Tres escolhas de desenho, todas com consequencia mensuravel:

1. Escala log1p. Contagens de dengue variam quatro ordens de grandeza entre o
   vale e o pico. Residuo aditivo e fortemente heterocedastico: um intervalo
   calibrado no pico fica absurdo no vale. Em log1p o residuo e aproximadamente
   estavel, e a volta por expm1 produz intervalo multiplicativo que respeita a
   nao negatividade da contagem.

2. Estratificacao por passo de horizonte. A incerteza cresce com h. Juntar h=1
   com h=12 daria intervalo largo demais em h=1 e estreito demais em h=12.

3. Quantil conformal com correcao de amostra finita, indice
   ceil((n+1)(1-alpha)) em vez do quantil empirico simples. Sem isso a cobertura
   fica sistematicamente abaixo do nominal com n pequeno.

A cobertura resultante e medida, nao assumida: ver evaluate_intervals().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZON = 12
MIN_CALIB_FOLDS = 20  # folds anteriores exigidos antes de emitir intervalo


def _conformal_quantile(residuals: np.ndarray, level: float) -> float:
    """Quantil conformal de amostra finita.

    level e a probabilidade acumulada desejada. Para n residuos, usa o
    k-esimo menor com k = ceil((n+1)*level), limitado a n.
    """
    n = residuals.size
    if n == 0:
        return np.nan
    k = int(np.ceil((n + 1) * level))
    if k < 1:
        return float(np.min(residuals))
    if k > n:
        return float(np.max(residuals))
    return float(np.partition(residuals, k - 1)[k - 1])


def add_fold_index(df: pd.DataFrame) -> pd.DataFrame:
    """Recupera fold e passo de horizonte a partir da ordem das linhas.

    O backtest grava os 12 alvos de cada fold em sequencia, e a origem avanca um
    mes por fold. A estrutura e verificada aqui em vez de assumida.
    """
    out = []
    for model, sub in df.groupby("model", sort=False):
        s = sub.reset_index(drop=True).copy()
        if len(s) % HORIZON != 0:
            raise ValueError(f"{model}: {len(s)} linhas nao e multiplo de {HORIZON}")
        s["fold"] = np.arange(len(s)) // HORIZON
        s["h"] = np.arange(len(s)) % HORIZON + 1

        dates = pd.to_datetime(s["date"])
        step = dates.groupby(s["fold"]).diff().dropna().dt.days
        if not step.between(28, 31).all():
            raise ValueError(f"{model}: alvos de um fold nao sao meses consecutivos")
        origins = dates[s["h"] == 1].reset_index(drop=True)
        adv = origins.diff().dropna().dt.days
        if not adv.between(28, 31).all():
            raise ValueError(f"{model}: origem nao avanca exatamente um mes por fold")
        out.append(s)
    return pd.concat(out, ignore_index=True)


def conformal_intervals(
    df: pd.DataFrame,
    levels: tuple[float, ...] = (0.50, 0.80, 0.95),
    min_calib_folds: int = MIN_CALIB_FOLDS,
    scale: str = "log1p",
) -> pd.DataFrame:
    """Anexa limites inferior e superior por nivel nominal.

    Espera as colunas model, date, y_true, y_pred, fold e h (ver add_fold_index).
    Linhas sem folds anteriores suficientes recebem NaN nos limites e ficam
    fora da avaliacao de cobertura.

    scale escolhe em que escala o residuo e calibrado, e a escolha nao e neutra:

      'log1p'    residuo multiplicativo. Acompanha a amplitude enorme da serie,
                 mas acopla os erros: um modelo que as vezes preve zero enquanto
                 ocorrem milhares de casos gera residuo de log1p(milhares), e
                 esse quantil infla o intervalo de TODAS as previsoes daquele
                 horizonte, inclusive as boas.
      'absolute' residuo aditivo. Nao tem esse acoplamento, mas produz largura
                 constante dentro de um horizonte, larga demais no vale entre
                 epidemias e estreita demais no pico.

    Nenhuma das duas e obviamente correta aqui, entao o manuscrito reporta as
    duas e so afirma o que sobrevive as duas.
    """
    if scale not in ("log1p", "absolute"):
        raise ValueError(f"scale desconhecida: {scale}")

    df = df.copy()
    for lv in levels:
        df[f"lo_{int(lv * 100)}"] = np.nan
        df[f"hi_{int(lv * 100)}"] = np.nan

    y_true = df["y_true"].to_numpy()
    y_pred = df["y_pred"].to_numpy()
    if scale == "log1p":
        df["_res"] = np.log1p(y_true) - np.log1p(y_pred)
        df["_anchor"] = np.log1p(y_pred)
        back = np.expm1
    else:
        df["_res"] = y_true - y_pred
        df["_anchor"] = y_pred
        back = lambda v: v  # noqa: E731

    for model, sub in df.groupby("model", sort=False):
        for h in range(1, HORIZON + 1):
            m = sub[sub["h"] == h].sort_values("fold")
            idx = m.index.to_numpy()
            res = m["_res"].to_numpy()
            anchor = m["_anchor"].to_numpy()

            for pos in range(len(idx)):
                if pos < min_calib_folds:
                    continue
                calib = res[:pos]  # so folds estritamente anteriores
                for lv in levels:
                    a = 1.0 - lv
                    q_lo = _conformal_quantile(calib, a / 2)
                    q_hi = _conformal_quantile(calib, 1 - a / 2)
                    df.at[idx[pos], f"lo_{int(lv * 100)}"] = max(0.0, back(anchor[pos] + q_lo))
                    df.at[idx[pos], f"hi_{int(lv * 100)}"] = max(0.0, back(anchor[pos] + q_hi))

    return df.drop(columns=["_res", "_anchor"])


def interval_score(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, alpha: float) -> np.ndarray:
    """Interval score de Gneiting e Raftery: largura mais penalidade por furo."""
    return (
        (hi - lo)
        + (2.0 / alpha) * np.clip(lo - y, 0, None)
        + (2.0 / alpha) * np.clip(y - hi, 0, None)
    )


def weighted_interval_score(
    y: np.ndarray, bounds: dict[float, tuple[np.ndarray, np.ndarray]], median: np.ndarray
) -> np.ndarray:
    """WIS de Bracher et al., o escore padrao dos forecast hubs epidemiologicos.

    Combina calibracao e nitidez num unico numero na escala do desfecho. Menor
    e melhor. bounds mapeia nivel nominal para (lo, hi).
    """
    k = len(bounds)
    total = 0.5 * np.abs(y - median)
    for lv, (lo, hi) in bounds.items():
        alpha = 1.0 - lv
        total = total + (alpha / 2.0) * interval_score(y, lo, hi, alpha)
    return total / (k + 0.5)


def evaluate_intervals(
    df: pd.DataFrame, levels: tuple[float, ...] = (0.50, 0.80, 0.95)
) -> dict:
    """Cobertura empirica, nitidez e WIS sobre as linhas que tem intervalo."""
    cols = [f"lo_{int(lv * 100)}" for lv in levels]
    ev = df.dropna(subset=cols).copy()
    if ev.empty:
        return {}

    y = ev["y_true"].to_numpy()
    out = {"n_evaluated": int(len(ev))}
    bounds = {}
    for lv in levels:
        p = int(lv * 100)
        lo = ev[f"lo_{p}"].to_numpy()
        hi = ev[f"hi_{p}"].to_numpy()
        bounds[lv] = (lo, hi)
        out[f"coverage_{p}"] = float(np.mean((y >= lo) & (y <= hi)))
        out[f"width_{p}"] = float(np.mean(hi - lo))
        out[f"median_width_{p}"] = float(np.median(hi - lo))
    out["WIS"] = float(np.mean(weighted_interval_score(y, bounds, ev["y_pred"].to_numpy())))
    return out
