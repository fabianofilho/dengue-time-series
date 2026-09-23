"""Testes do piso da comparação e das colunas de pareamento.

O naive sazonal é o denominador de tudo que vier depois: se ele estiver errado,
todo veredito sobre "o modelo bate o baseline" fica errado junto, e em silêncio,
porque um naive sazonal com defeito ainda produz números plausíveis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dengue_forecast.evaluate import run_backtest
from dengue_forecast.models import SeasonalNaiveForecaster


def serie(n: int, start: str = "2010-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=n, freq="MS")
    return pd.Series(np.arange(1.0, n + 1.0), index=idx)


def test_repete_o_mesmo_mes_do_ano_anterior():
    s = serie(36)
    pred = SeasonalNaiveForecaster().forecast(s, horizon=12)
    # Os 12 últimos observados, na mesma ordem: jan previsto = jan anterior.
    assert np.array_equal(pred, s.iloc[-12:].to_numpy())


def test_horizonte_maior_que_um_ciclo_reinicia_a_estacao():
    s = serie(36)
    pred = SeasonalNaiveForecaster().forecast(s, horizon=18)
    ultima = s.iloc[-12:].to_numpy()
    assert np.array_equal(pred[:12], ultima)
    assert np.array_equal(pred[12:], ultima[:6])


def test_sazonalidade_de_verdade_e_repetida():
    # Padrão sazonal explícito, para não passar só por causa da série crescente.
    idx = pd.date_range("2010-01-01", periods=24, freq="MS")
    padrao = np.array([10.0, 20, 50, 400, 900, 300, 80, 40, 20, 15, 12, 11])
    s = pd.Series(np.concatenate([padrao, padrao * 2]), index=idx)
    pred = SeasonalNaiveForecaster().forecast(s, horizon=12)
    assert np.array_equal(pred, padrao * 2)


def test_serie_mais_curta_que_um_ciclo_cai_para_o_ultimo_valor():
    s = serie(7)
    pred = SeasonalNaiveForecaster().forecast(s, horizon=5)
    assert np.array_equal(pred, np.full(5, s.iloc[-1]))


def test_exatamente_um_ciclo_ja_usa_a_estacao():
    # Fronteira: len(train) == season_length nao deve cair no fallback.
    s = serie(12)
    pred = SeasonalNaiveForecaster().forecast(s, horizon=12)
    assert np.array_equal(pred, s.to_numpy())


def test_backtest_grava_window_e_horizon_coerentes():
    s = serie(72)
    _metric, preds, skipped = run_backtest(
        series=s, model=SeasonalNaiveForecaster(), horizon=12, min_train_size=48
    )
    assert skipped == []
    n_janelas = 72 - 12 - 48 + 1
    assert preds["window"].max() == n_janelas
    assert len(preds) == n_janelas * 12
    assert sorted(preds["horizon"].unique()) == list(range(1, 13))
    # Cada janela tem os 12 passos, e a origem avança exatamente um mês.
    assert (preds.groupby("window").size() == 12).all()
    primeiros = preds[preds["horizon"] == 1].sort_values("window")["date"]
    assert (pd.to_datetime(primeiros).diff().dropna().dt.days.between(28, 31)).all()


def test_janela_nao_finita_e_descartada_e_reportada():
    class Explode(SeasonalNaiveForecaster):
        name = "explode"

        def forecast(self, train, horizon):
            out = super().forecast(train, horizon)
            if len(train) == 48:  # só a primeira janela
                out = out.copy()
                out[0] = np.inf
            return out

    s = serie(72)
    _metric, preds, skipped = run_backtest(
        series=s, model=Explode(), horizon=12, min_train_size=48
    )
    assert skipped == [1]
    assert 1 not in set(preds["window"])
    assert np.isfinite(preds["y_pred"]).all()


def test_modelo_que_falha_em_tudo_nao_devolve_metrica():
    class Quebrado(SeasonalNaiveForecaster):
        name = "quebrado"

        def forecast(self, train, horizon):
            raise RuntimeError("sem biblioteca")

    s = serie(72)
    metric, preds, skipped = run_backtest(
        series=s, model=Quebrado(), horizon=12, min_train_size=48
    )
    assert metric is None
    assert preds.empty
    assert len(skipped) == 72 - 12 - 48 + 1


def test_nome_de_modelo_invalido_e_recusado():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from run_benchmark import build_models

    with pytest.raises(ValueError, match="Modelos inválidos"):
        build_models(["seasonal_naive", "sarimx"], lags=24)
