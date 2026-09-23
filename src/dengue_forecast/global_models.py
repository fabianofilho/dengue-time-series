"""Modelos globais: um único modelo treinado nas 8 cidades ao mesmo tempo.

O que isto responde: o benchmark treina um modelo por cidade, e isso presume que
não há nada a aprender de uma cidade que sirva para outra. Um modelo global
testa essa premissa. As 8 séries compartilham o mesmo calendário, a mesma
sazonalidade de verão e a mesma epidemia de 2024, então há motivo para achar que
pooling ajuda, e esse motivo precisa ser medido, não assumido.

Duas decisões de especificação que mudam o resultado e por isso ficam escritas:

1. `transformer_series=StandardScaler()`, padronização POR SÉRIE. São Paulo tem
   média mensal de 9.566 casos e Salvador 653, quinze vezes menos. Sem
   padronizar, o erro quadrático do treino conjunto é dominado por São Paulo e
   Belo Horizonte, e o modelo "global" vira um modelo de São Paulo aplicado às
   outras sete. Isto não é o mesmo assunto da armadilha do Ridge documentada no
   CLAUDE.md: lá o problema era condicionamento numérico dentro de uma série,
   aqui é o peso relativo entre séries. Por isso vale também para as árvores,
   que são invariantes a escala dentro de uma série mas não à mistura delas.

2. `encoding="onehot"`. A identidade da cidade entra como indicadora, não como
   inteiro. O default do skforecast é "ordinal", que numera as séries e impõe
   uma ordem inexistente entre elas, e essa ordem é uma variável que os modelos
   de árvore usam para partir.

A comparação honesta é entre o mesmo estimador nas duas formas: lgbm contra
global_lgbm, e assim por diante. Comparar um global de um estimador com um local
de outro mistura dois efeitos.

SARIMAX e TimesFM não têm forma global aqui: o SARIMAX é por série na definição,
e o TimesFM já é pré-treinado em muitas séries, que é a versão extrema disto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from skforecast.recursive import ForecasterRecursiveMultiSeries
from xgboost import XGBRegressor

PREFIX = "global_"


class GlobalForecaster:
    """Um modelo, várias séries. Prevê todas as cidades de uma vez.

    A interface é diferente da de `Forecaster` de propósito: aquela recebe uma
    série e devolve um vetor, e um modelo global não cabe nela sem fingir que
    cada cidade é um ajuste separado, que é exatamente o que ele não é.
    """

    def __init__(
        self,
        estimator,
        lags: int = 24,
        name: str | None = None,
        encoding: str = "onehot",
        scale_series: bool = True,
    ):
        self.estimator = estimator
        self.lags = lags
        self.encoding = encoding
        self.scale_series = scale_series
        base = estimator.__class__.__name__.lower().replace("regressor", "")
        self.name = name or f"{PREFIX}{base}"

    def forecast(self, train: pd.DataFrame, horizon: int) -> pd.DataFrame:
        """`train` tem uma coluna por cidade. Devolve horizon x n_cidades."""
        forecaster = ForecasterRecursiveMultiSeries(
            estimator=self.estimator,
            lags=self.lags,
            encoding=self.encoding,
            transformer_series=StandardScaler() if self.scale_series else None,
        )
        forecaster.fit(series=train, suppress_warnings=True)
        pred = forecaster.predict(steps=horizon, levels=list(train.columns))
        # skforecast 0.23 devolve formato longo: indice de data, colunas
        # level e pred. O pivot reordena por nome, entao as colunas e as
        # linhas sao reindexadas de volta para a ordem de entrada, que e a
        # ordem em que o chamador espera as cidades.
        wide = pred.pivot(columns="level", values="pred")
        wide = wide.reindex(columns=list(train.columns))
        if wide.isna().any().any():
            raise ValueError("Previsao global com NaN apos o pivot")
        # Mesma regra dos modelos locais: contagem não é negativa.
        return wide.clip(lower=0.0)


def global_lgbm(lags: int = 24, **kw) -> GlobalForecaster:
    return GlobalForecaster(
        LGBMRegressor(random_state=42, verbose=-1), lags=lags, name="global_lgbm", **kw
    )


def global_xgboost(lags: int = 24, **kw) -> GlobalForecaster:
    return GlobalForecaster(
        XGBRegressor(random_state=42, objective="reg:squarederror"),
        lags=lags,
        name="global_xgboost",
        **kw,
    )


def global_catboost(lags: int = 24, **kw) -> GlobalForecaster:
    return GlobalForecaster(
        CatBoostRegressor(random_state=42, verbose=0), lags=lags, name="global_catboost", **kw
    )


def global_randomforest(lags: int = 24, **kw) -> GlobalForecaster:
    return GlobalForecaster(
        RandomForestRegressor(random_state=42, n_estimators=100),
        lags=lags,
        name="global_randomforest",
        **kw,
    )


def global_ridge(lags: int = 24, **kw) -> GlobalForecaster:
    return GlobalForecaster(Ridge(random_state=42), lags=lags, name="global_ridge", **kw)


BUILDERS = {
    "global_lgbm": global_lgbm,
    "global_xgboost": global_xgboost,
    "global_catboost": global_catboost,
    "global_randomforest": global_randomforest,
    "global_ridge": global_ridge,
}

# Par local correspondente, que é com quem cada global tem que ser comparado.
LOCAL_COUNTERPART = {
    "global_lgbm": "lgbm",
    "global_xgboost": "xgboost",
    "global_catboost": "catboost",
    "global_randomforest": "randomforest",
    "global_ridge": "ridge",
}


def build_global_models(names: list[str], lags: int = 24, **kw) -> list[GlobalForecaster]:
    selected = [n.strip().lower() for n in names if n.strip()]
    invalid = set(selected) - set(BUILDERS)
    if invalid:
        raise ValueError(f"Modelos globais inválidos: {sorted(invalid)}")
    return [BUILDERS[n](lags=lags, **kw) for n in selected]


def to_wide(series_por_cidade: dict[str, pd.Series]) -> pd.DataFrame:
    """Empilha as séries em colunas, exigindo que compartilhem o índice.

    Se os índices não baterem, o pooling silenciosamente alinharia por data e
    preencheria buracos com NaN, e o modelo global teria menos dado do que o
    local sem que nada avisasse.
    """
    nomes = list(series_por_cidade)
    idx = series_por_cidade[nomes[0]].index
    for nome in nomes[1:]:
        if not series_por_cidade[nome].index.equals(idx):
            raise ValueError(f"{nome} nao compartilha o indice de {nomes[0]}")
    wide = pd.DataFrame({n: series_por_cidade[n] for n in nomes})
    if wide.isna().any().any():
        raise ValueError("Ha NaN apos o empilhamento das series")
    return wide.astype(float)
