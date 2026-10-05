"""Testes das variantes _log (emenda exploratória de 2026-10-04).

A variante ajusta em log1p(y) e devolve a previsão em casos. Os riscos que estes
testes cobrem são os silenciosos: a variante bruta mudar sem querer (o default
publicado tem que continuar idêntico), a previsão voltar em escala log, e uma
recursão divergente na escala log virar infinito no expm1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dengue_forecast.models import (
    LOG_CAP,
    SarimaxForecaster,
    _from_log,
    catboost_forecaster,
    randomforest_forecaster,
    ridge_forecaster,
)


def serie_epidemica(n: int = 72) -> pd.Series:
    """Sazonal com picos de magnitude variável, como as séries de dengue."""
    idx = pd.date_range("2010-01-01", periods=n, freq="MS")
    rng = np.random.default_rng(0)
    base = 200 + 150 * np.sin(2 * np.pi * np.arange(n) / 12)
    picos = np.where(np.arange(n) % 12 == 3, rng.uniform(1, 30, n), 1.0)
    return pd.Series(base * picos, index=idx)


def test_nomes_ganham_sufixo_e_o_bruto_continua_igual():
    assert randomforest_forecaster().name == "randomforest"
    assert randomforest_forecaster(log_target=True).name == "randomforest_log"
    assert SarimaxForecaster().name == "sarimax"
    assert SarimaxForecaster(log_target=True).name == "sarimax_log"


@pytest.mark.parametrize("factory", [randomforest_forecaster, ridge_forecaster, catboost_forecaster])
def test_previsao_volta_na_escala_de_casos(factory):
    s = serie_epidemica()
    pred = factory(log_target=True).forecast(s, horizon=12)
    assert pred.shape == (12,)
    assert np.all(np.isfinite(pred)) and np.all(pred >= 0)
    # Em escala log os valores ficariam abaixo de ~10; em casos, na ordem da série.
    assert pred.max() > 50


def test_variante_log_da_arvore_pode_passar_do_maximo_do_treino():
    # O motivo da emenda: em escala bruta, a árvore nunca prevê acima do máximo
    # visto no treino. Em log isso também vale para log1p(y), mas a média de
    # folhas em log, depois do expm1, não é limitada pela média de folhas em casos.
    s = serie_epidemica()
    bruto = randomforest_forecaster().forecast(s, horizon=12)
    assert bruto.max() <= s.max() + 1e-9


def test_teto_impede_infinito_quando_a_recursao_diverge():
    s = pd.Series([10.0, 100.0, 1000.0])
    z = np.array([1e3, np.log1p(50.0)])  # 1e3 em log estouraria o float no expm1
    out = _from_log(z, s)
    assert np.all(np.isfinite(out))
    assert out[0] == pytest.approx(np.expm1(np.log1p(1000.0) + LOG_CAP))
    assert out[1] == pytest.approx(50.0)
