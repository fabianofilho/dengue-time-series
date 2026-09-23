"""Testes do modelo global.

O que protegem: o global prevê 8 cidades de uma vez e o skforecast devolve
formato longo, então há um pivot no caminho. Pivot reordena por nome, e um
erro aí não levanta exceção: ele troca as previsões de cidade entre si e produz
um CSV perfeitamente bem formado com os números nas linhas erradas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from dengue_forecast.global_models import (
    BUILDERS,
    LOCAL_COUNTERPART,
    GlobalForecaster,
    build_global_models,
    to_wide,
)


def series_de(nomes: list[str], n: int = 80) -> dict[str, pd.Series]:
    idx = pd.date_range("2010-01-01", periods=n, freq="MS")
    rng = np.random.default_rng(0)
    saida = {}
    for i, nome in enumerate(nomes):
        sazonal = 100.0 * (i + 1) * (1 + np.sin(np.arange(n) * 2 * np.pi / 12))
        saida[nome] = pd.Series(sazonal + rng.normal(0, 5, n), index=idx).clip(lower=0)
    return saida


def test_to_wide_recusa_indices_diferentes():
    s = series_de(["a", "b"])
    s["b"] = s["b"].iloc[1:]
    with pytest.raises(ValueError, match="nao compartilha o indice"):
        to_wide(s)


def test_to_wide_recusa_nan():
    s = series_de(["a", "b"])
    s["b"].iloc[3] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        to_wide(s)


def test_to_wide_preserva_a_ordem_das_colunas():
    s = series_de(["zulu", "alfa", "mike"])
    assert list(to_wide(s).columns) == ["zulu", "alfa", "mike"]


def test_previsao_sai_na_ordem_de_entrada_nao_na_alfabetica():
    """O pivot do skforecast ordena por nome. Se a reindexação sumir, as colunas
    voltam em ordem alfabética e cada cidade recebe a previsão de outra."""
    nomes = ["zulu", "alfa", "mike"]
    wide = to_wide(series_de(nomes))
    modelo = GlobalForecaster(Ridge(random_state=42), lags=12, name="global_teste")
    pred = modelo.forecast(wide.iloc[:60], horizon=12)
    assert list(pred.columns) == nomes
    assert list(pred.columns) != sorted(nomes)


def test_cada_cidade_recebe_a_propria_previsao():
    """Séries de magnitude muito diferente: a previsão de cada coluna tem que
    ficar na ordem de grandeza daquela coluna, não da vizinha."""
    idx = pd.date_range("2010-01-01", periods=80, freq="MS")
    base = 1 + np.sin(np.arange(80) * 2 * np.pi / 12)
    s = {
        "grande": pd.Series(10_000.0 * base + 10_000, index=idx),
        "pequena": pd.Series(10.0 * base + 10, index=idx),
    }
    wide = to_wide(s)
    pred = GlobalForecaster(Ridge(random_state=42), lags=12).forecast(wide.iloc[:60], horizon=12)
    assert pred["grande"].mean() > 1_000
    assert pred["pequena"].mean() < 1_000


def test_previsao_tem_a_forma_pedida_e_nao_e_negativa():
    wide = to_wide(series_de(["a", "b", "c"]))
    pred = GlobalForecaster(Ridge(random_state=42), lags=12).forecast(wide.iloc[:60], horizon=6)
    assert pred.shape == (6, 3)
    assert (pred.to_numpy() >= 0).all()


def test_nome_de_modelo_global_invalido_e_recusado():
    with pytest.raises(ValueError, match="Modelos globais inválidos"):
        build_global_models(["global_lgbm", "global_sarimax"])


def test_todo_global_tem_par_local_declarado():
    """Sem o par local, comparar o global com qualquer outro modelo mistura o
    efeito de agrupar as cidades com o efeito de trocar de estimador."""
    assert set(BUILDERS) == set(LOCAL_COUNTERPART)


def test_nomes_seguem_o_prefixo():
    for nome, builder in BUILDERS.items():
        assert builder().name == nome
        assert nome.startswith("global_")


def test_desligar_a_padronizacao_muda_a_previsao():
    """Se o transformer_series não estivesse sendo aplicado, ligar e desligar
    daria o mesmo número, e a rodada de sensibilidade seria uma cópia."""
    idx = pd.date_range("2010-01-01", periods=80, freq="MS")
    base = 1 + np.sin(np.arange(80) * 2 * np.pi / 12)
    wide = to_wide(
        {
            "grande": pd.Series(10_000.0 * base + 10_000, index=idx),
            "pequena": pd.Series(10.0 * base + 10, index=idx),
        }
    )
    com = GlobalForecaster(Ridge(random_state=42), lags=12, scale_series=True)
    sem = GlobalForecaster(Ridge(random_state=42), lags=12, scale_series=False)
    a = com.forecast(wide.iloc[:60], horizon=6)
    b = sem.forecast(wide.iloc[:60], horizon=6)
    assert not np.allclose(a.to_numpy(), b.to_numpy())


def test_janelas_do_global_batem_com_as_do_local():
    """O global tem que percorrer exatamente as mesmas janelas do backtest local,
    senão as previsões não pareiam no bootstrap."""
    from dengue_forecast.evaluate import rolling_origin_splits

    wide = to_wide(series_de(["a", "b"], n=72))
    uma = wide["a"]
    j_global = list(rolling_origin_splits(wide, horizon=12, min_train_size=48))
    j_local = list(rolling_origin_splits(uma, horizon=12, min_train_size=48))
    assert len(j_global) == len(j_local) == 72 - 12 - 48 + 1
    for (tg, eg), (tl, el) in zip(j_global, j_local):
        assert tg.index.equals(tl.index)
        assert eg.index.equals(el.index)
