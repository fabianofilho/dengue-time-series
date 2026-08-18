"""
Conversao de semanas epidemiologicas em meses de calendario.

Vive no pacote, e nao em scripts/, para poder ser testada. A versao anterior
desta logica estava embutida em scripts/process_data.py sem teste, e continha o
erro descrito em weekly_to_monthly.
"""
from __future__ import annotations

import pandas as pd

WEEK_TAIL = pd.Timedelta(days=6)  # do inicio da semana ate o seu ultimo dia


def weekly_to_monthly(weekly: pd.Series, verbose: bool = True) -> pd.Series:
    """Converte contagem semanal em contagem mensal de calendario.

    O erro que isto corrige: agregar por resample("MS").sum() sobre a data de
    INICIO da semana joga a semana inteira no mes em que caiu o domingo dela.
    O resultado nao e uma serie mensal, e "soma das 4 ou 5 semanas que
    comecaram neste mes". Na serie do InfoDengue usada aqui, 118 dos 180 meses
    somavam 28 dias de casos e 62 somavam 35: uma oscilacao artificial de 25%
    ditada pelo calendario, com periodo de aproximadamente 12,4 meses, que nem
    se alinha a sazonalidade anual.

    Aqui cada semana e espalhada uniformemente pelos 7 dias que cobre, e a soma
    e feita por mes de calendario. A uniformidade dentro da semana e uma
    aproximacao, mas erra por dias dentro de uma semana, nao por semanas
    inteiras entre meses.

    Meses cobertos apenas em parte pela serie semanal sao descartados: um mes
    com 28 dos 31 dias observados nao e comparavel aos demais.
    """
    if weekly.empty:
        return weekly.astype(int)

    idx = pd.DatetimeIndex(weekly.index)
    days = pd.date_range(idx.min(), idx.max() + WEEK_TAIL, freq="D")
    daily = pd.Series(0.0, index=days)
    for start, cases in zip(idx, weekly.to_numpy(dtype=float)):
        daily.loc[start : start + WEEK_TAIL] += cases / 7.0

    monthly = daily.resample("MS").sum()
    observed = daily.resample("MS").size()
    complete = observed == monthly.index.days_in_month

    if verbose and (~complete).any():
        dropped = ", ".join(d.strftime("%Y-%m") for d in monthly.index[~complete])
        print(f"  [INFO] meses incompletos descartados: {dropped}")

    return monthly[complete].round().astype(int)
