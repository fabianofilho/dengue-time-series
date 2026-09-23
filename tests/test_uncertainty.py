"""Testes do módulo de incerteza portado de onco_timeseries.

O que estes testes protegem: um erro aqui não levanta exceção nem produz valor
absurdo, produz um intervalo mais estreito do que deveria, e intervalo estreito
é exatamente o que faz diferença de ruído parecer achado.
"""
from __future__ import annotations

import numpy as np
import pytest

from dengue_forecast.uncertainty import (
    bootstrap_metrica,
    dm_test,
    ic_percentil,
    p_bicaudal,
    sortear_janelas,
)


def test_sorteio_e_deterministico_e_tem_a_forma_certa():
    a = sortear_janelas(119, 500, 20260817)
    b = sortear_janelas(119, 500, 20260817)
    assert a.shape == (500, 119)
    assert np.array_equal(a, b)
    assert a.min() >= 0 and a.max() <= 118


def test_semente_diferente_muda_o_sorteio():
    a = sortear_janelas(119, 500, 20260817)
    b = sortear_janelas(119, 500, 1)
    assert not np.array_equal(a, b)


def test_bootstrap_reamostra_janela_inteira_nao_previsao_isolada():
    # Janela constante por linha: se a reamostragem fosse por previsão, a média
    # da réplica poderia cair entre os valores das linhas. Reamostrando linhas
    # inteiras, toda réplica é uma média de valores do próprio conjunto.
    mat = np.repeat(np.arange(10.0).reshape(10, 1), 6, axis=1)
    idx = sortear_janelas(10, 200, 7)
    boot = bootstrap_metrica(mat, idx)
    assert boot.shape == (200,)
    assert boot.min() >= 0.0 and boot.max() <= 9.0


def test_bootstrap_de_matriz_constante_nao_tem_dispersao():
    mat = np.full((20, 12), 3.0)
    boot = bootstrap_metrica(mat, sortear_janelas(20, 300, 3))
    assert np.allclose(boot, 3.0)
    lo, hi = ic_percentil(boot)
    assert lo == pytest.approx(3.0) and hi == pytest.approx(3.0)


def test_ic_percentil_cobre_o_nivel_pedido():
    boot = np.arange(1000.0)
    lo, hi = ic_percentil(boot, nivel=95.0)
    assert lo == pytest.approx(np.percentile(boot, 2.5))
    assert hi == pytest.approx(np.percentile(boot, 97.5))
    lo80, hi80 = ic_percentil(boot, nivel=80.0)
    assert lo80 > lo and hi80 < hi


def test_p_bicaudal_nunca_passa_de_um():
    # Diferença centrada em zero: as duas frações somam mais que 1 e dobrar a
    # menor delas passaria de 1 sem o limite.
    d = np.array([-1.0, 0.0, 0.0, 1.0])
    assert p_bicaudal(d) <= 1.0


def test_p_bicaudal_e_pequeno_quando_tudo_esta_de_um_lado():
    assert p_bicaudal(np.ones(1000)) == pytest.approx(0.0)


def test_dm_nao_rejeita_diferenca_de_ruido():
    rng = np.random.default_rng(0)
    d = rng.normal(0.0, 1.0, size=119)
    _estat, p = dm_test(d, h=1)
    assert p > 0.05


def test_dm_rejeita_diferenca_sistematica():
    rng = np.random.default_rng(0)
    d = rng.normal(2.0, 0.5, size=119)
    estat, p = dm_test(d, h=1)
    assert estat > 0
    assert p < 0.01


def test_dm_e_invariante_a_escala():
    """O critério testa a perda relativa, que é a perda absoluta dividida por
    uma constante da cidade. Se DM não fosse invariante a escala, dividir mudaria
    o veredito, e o arquivo de resultados diria "relmae" sobre outro teste."""
    rng = np.random.default_rng(1)
    d = rng.normal(0.3, 1.0, size=119)
    a = dm_test(d, h=6)
    b = dm_test(d / 1134.0, h=6)
    assert a[0] == pytest.approx(b[0])
    assert a[1] == pytest.approx(b[1])


def test_dm_devolve_nan_quando_a_variancia_de_longo_prazo_nao_serve():
    # Série alternante: as autocovariâncias negativas derrubam a variância de
    # longo prazo abaixo de zero, e o truncamento deixa de ser confiável.
    d = np.array([1.0, -1.0] * 60)
    estat, p = dm_test(d, h=12)
    assert np.isnan(estat) and np.isnan(p)


def test_correcao_de_harvey_encolhe_a_estatistica():
    rng = np.random.default_rng(2)
    d = rng.normal(0.5, 1.0, size=119)
    est_h1, _ = dm_test(d, h=1)
    n = len(d)
    bruto = d.mean() / np.sqrt((np.sum((d - d.mean()) ** 2) / n) / n)
    assert abs(est_h1) < abs(bruto)
