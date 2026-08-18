"""
Testes da conversao de semana epidemiologica para mes de calendario.

O teste central e o de conservacao mais o de nao oscilacao: a agregacao antiga
passava no primeiro e falhava no segundo, que e exatamente o bug que ela tinha.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dengue_forecast.preprocess import weekly_to_monthly


def epi_weeks(start="2010-01-03", n=782, value=700.0):
    """Semanas de domingo em domingo, como o InfoDengue entrega."""
    idx = pd.date_range(start, periods=n, freq="7D")
    return pd.Series([value] * n, index=idx)


def test_empty_input():
    out = weekly_to_monthly(pd.Series(dtype=float), verbose=False)
    assert out.empty


def test_conserves_cases_within_complete_months():
    w = epi_weeks(n=200, value=700.0)
    m = weekly_to_monthly(w, verbose=False)
    # o que sobra fora dos meses completos e o unico vazamento admitido
    daily_total = w.sum()
    assert m.sum() <= daily_total
    assert m.sum() > daily_total * 0.97


def test_constant_rate_gives_proportional_months():
    """Com 100 casos por dia, cada mes deve receber 100 vezes seus dias.

    Este e o teste que a agregacao antiga falhava: ela dava 2800 ou 3500 por
    mes conforme o calendario, em vez de 2800, 3000 ou 3100 conforme os dias.
    """
    w = epi_weeks(n=300, value=700.0)  # 700 por semana = 100 por dia
    m = weekly_to_monthly(w, verbose=False)
    expected = m.index.days_in_month * 100
    assert np.allclose(m.to_numpy(), expected, atol=1.0)


def test_no_calendar_oscillation():
    """Sob taxa constante, a variacao mes a mes deve refletir so os dias do mes."""
    w = epi_weeks(n=300, value=700.0)
    m = weekly_to_monthly(w, verbose=False)
    per_day = m / m.index.days_in_month
    assert per_day.std() < 0.5, "taxa diaria deveria ser praticamente constante"
    # a agregacao antiga produzia razao 35/28 = 1.25 entre meses vizinhos
    ratio = (m / m.shift()).dropna()
    assert ratio.max() < 1.15, f"oscilacao de calendario ainda presente: {ratio.max():.2f}"


def test_drops_incomplete_boundary_months():
    """Serie que comeca em 03/01 e termina no meio do mes perde as duas pontas."""
    w = epi_weeks(start="2010-01-03", n=52)  # cobre ate 2010-12-31 aprox
    m = weekly_to_monthly(w, verbose=False)
    assert pd.Timestamp("2010-01-01") not in m.index, "janeiro esta incompleto"
    assert m.index.min() == pd.Timestamp("2010-02-01")


def test_month_fully_covered_is_kept():
    w = epi_weeks(start="2010-01-03", n=60)
    m = weekly_to_monthly(w, verbose=False)
    for ts in m.index:
        assert ts.day == 1
    assert (m > 0).all()


def test_spike_is_split_across_the_month_boundary():
    """Uma semana a cavaleiro de dois meses tem que dividir os casos entre eles."""
    # semana comecando em 2010-01-31: 1 dia em janeiro, 6 em fevereiro
    w = pd.Series([0.0] * 10, index=pd.date_range("2010-01-03", periods=10, freq="7D"))
    w.loc[pd.Timestamp("2010-01-31")] = 700.0
    m = weekly_to_monthly(w, verbose=False)
    # janeiro cai fora por estar incompleto, mas fevereiro deve ficar com 6/7
    assert m.loc[pd.Timestamp("2010-02-01")] == pytest.approx(600, abs=1)


def test_matches_real_series_shape():
    """Regressao contra a serie real: 782 semanas devem virar 178 meses."""
    w = epi_weeks(start="2010-01-03", n=782)
    m = weekly_to_monthly(w, verbose=False)
    assert len(m) == 178
    assert m.index.min() == pd.Timestamp("2010-02-01")
    assert m.index.max() == pd.Timestamp("2024-11-01")
