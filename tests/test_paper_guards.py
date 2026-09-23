"""Testes das guardas que impedem numero publicado de mudar em silencio.

Contexto: os CSVs de results/ passaram a conter 13 modelos (7 do artigo, o piso
sazonal e 5 globais). Toda contagem "por cidade" nas tabelas e figuras do artigo
e feita sobre os modelos presentes no arquivo, entao acrescentar modelo muda
numero publicado sem levantar exceção nenhuma. Foi o que aconteceu com a linha
"TimesFM ranked first" da Tabela 7, com a coluna de vitorias da Tabela 5 e com o
painel de cobertura ao longo do tempo da Figura 6.

Estes testes existem para que a proxima pessoa que acrescentar um modelo veja
uma falha em vez de um numero diferente.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_paper_assets as bpa  # noqa: E402
import run_ensembles as ens  # noqa: E402


# --------------------------------------------------------------- run_ensembles
def test_grupo_publicados_e_o_conjunto_do_artigo():
    assert ens.resolve_members("publicados") == ens.PUBLICADOS
    assert set(ens.PUBLICADOS) == set(bpa.MODELS)


def test_grupos_se_somam_sem_repetir():
    m = ens.resolve_members("publicados,globais")
    assert m == ens.PUBLICADOS + ens.GLOBAIS
    assert len(m) == len(set(m)) == 12


def test_nome_solto_e_aceito_junto_com_grupo():
    m = ens.resolve_members("publicados,global_ridge")
    assert m[-1] == "global_ridge"
    assert len(m) == 8


def test_membro_repetido_nao_entra_duas_vezes():
    m = ens.resolve_members("publicados,timesfm")
    assert m == ens.PUBLICADOS


def test_ensemble_de_um_membro_so_e_recusado():
    with pytest.raises(ValueError, match="ao menos 2 membros"):
        ens.resolve_members("timesfm")


def test_piso_sazonal_nao_e_membro_do_ensemble():
    """Ele e a regua contra a qual o ensemble e julgado. Regua e competidor no
    mesmo numero tornaria a comparacao circular."""
    assert "seasonal_naive" not in ens.resolve_members("publicados,globais")


# ------------------------------------------------------- build_paper_assets
def frame_ensemble(membros: list[str]) -> pd.DataFrame:
    linhas = []
    for city in ("sao_paulo", "rio"):
        for m in membros:
            linhas.append(
                {"city": city, "approach": m, "kind": "member",
                 "sMAPE": 80.0, "MAE": 100.0, "RMSE": 200.0, "n": 1188}
            )
        for e in ("mean", "median"):
            linhas.append(
                {"city": city, "approach": e, "kind": "ensemble",
                 "sMAPE": 79.0, "MAE": 99.0, "RMSE": 199.0, "n": 1188}
            )
    return pd.DataFrame(linhas)


def test_table6_aceita_o_conjunto_publicado():
    tex, resumo = bpa.table6(frame_ensemble(bpa.MODELS))
    assert "tab:ensembles" in tex or "ensemble" in tex.lower()
    assert "n_cities_ensemble_beats_best_member" in resumo


def test_table6_recusa_o_arquivo_com_os_globais():
    """Trocar o arquivo de entrada nao pode render uma Tabela 6 diferente em
    silencio: o conjunto de membros muda toda abordagem, inclusive a mediana."""
    with pytest.raises(ValueError, match="ensemble_summary_with_global"):
        bpa.table6(frame_ensemble(bpa.MODELS + ["global_ridge"]))


def test_table6_recusa_membro_faltando():
    with pytest.raises(ValueError, match="esperado"):
        bpa.table6(frame_ensemble([m for m in bpa.MODELS if m != "lgbm"]))


def test_filtro_de_carga_derruba_modelo_extra():
    df = pd.DataFrame({"model": bpa.MODELS + ["global_ridge", "seasonal_naive"]})
    out = bpa._so_publicados(df, "teste")
    assert set(out["model"]) == set(bpa.MODELS)


def test_filtro_de_carga_recusa_modelo_do_artigo_ausente():
    df = pd.DataFrame({"model": [m for m in bpa.MODELS if m != "timesfm"]})
    with pytest.raises(ValueError, match="ausentes"):
        bpa._so_publicados(df, "teste")


def test_horizon_metrics_ignora_modelo_de_fora():
    """A linha "TimesFM ranked first" da Tabela 7 conta por horizonte sobre os
    modelos presentes, entao o filtro tem que estar dentro de horizon_metrics."""
    idx = pd.date_range("2014-02-01", periods=12, freq="MS")
    linhas = []
    for m in bpa.MODELS + ["global_ridge"]:
        for h, dt in enumerate(idx, start=1):
            linhas.append({"model": m, "date": dt, "y_true": 100.0, "y_pred": 90.0})
    hor = bpa.horizon_metrics({"Sao Paulo": pd.DataFrame(linhas)})
    assert set(hor["model"]) == set(bpa.MODELS)
