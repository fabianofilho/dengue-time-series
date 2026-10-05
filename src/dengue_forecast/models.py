"""
Implementação dos modelos de forecasting usando skforecast.

Modelos incluídos:
- Naive sazonal (piso da comparação)
- SARIMAX (baseline estatístico)
- Prophet (Meta)
- LightGBM
- XGBoost
- CatBoost
- RandomForest
- Ridge
- TimesFM (Google, zero-shot foundation model)

Variantes "_log" (emenda exploratória de 2026-10-04, ver results/criterion.json):
SARIMAX e os modelos de skforecast ajustados em log1p(y), com a previsão devolvida
na escala original por expm1. Árvores ajustadas na contagem bruta não conseguem
prever acima do máximo do treino, o que as prejudica em anos de epidemia recorde.
"""
from __future__ import annotations

import warnings
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

# timesfm deve ser importado antes de catboost/lightgbm/xgboost para evitar
# conflito de bibliotecas nativas que causa segfault no macOS ARM
try:
    import timesfm as _timesfm
    _TIMESFM_AVAILABLE = True
except ImportError:
    _TIMESFM_AVAILABLE = False

from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from skforecast.recursive import ForecasterRecursive
from statsmodels.tsa.statespace.sarimax import SARIMAX
from xgboost import XGBRegressor

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    from skforecast.exceptions import IgnoredArgumentWarning
    warnings.filterwarnings("ignore", category=IgnoredArgumentWarning)
except ImportError:
    pass


class Forecaster(ABC):
    """Interface para todos os modelos de forecasting."""

    name: str

    @abstractmethod
    def forecast(self, train: pd.Series, horizon: int) -> np.ndarray:
        """Recebe a série de treino e retorna a previsão para o horizonte."""
        pass


class SeasonalNaiveForecaster(Forecaster):
    """Repete o valor observado no mesmo mês do ano anterior.

    É o piso da comparação. Um modelo que não bate isto não aprendeu nada que a
    sazonalidade sozinha já não diga, e sem esta linha o benchmark compara sete
    modelos entre si sem dizer se algum deles vale a pena.

    Portado de onco_timeseries.models, sem os parâmetros exógenos, que a
    interface Forecaster deste repo não tem.
    """

    name = "seasonal_naive"

    def __init__(self, season_length: int = 12):
        self.season_length = season_length

    def forecast(self, train: pd.Series, horizon: int) -> np.ndarray:
        m = self.season_length
        if len(train) < m:
            # Sem um ciclo completo, cai para o último valor observado.
            return np.full(horizon, float(train.iloc[-1]))

        last_season = np.asarray(train.iloc[-m:], dtype=float)
        idx = np.arange(horizon) % m
        return last_season[idx]


LOG_CAP = 5.0  # teto em escala log acima de log1p(max do treino): ~148x o maximo


def _log_name(name: str, log_target: bool) -> str:
    return f"{name}_log" if log_target else name


def _from_log(z: np.ndarray, train: pd.Series) -> np.ndarray:
    """expm1 com teto: evita overflow quando uma recursao diverge na escala log."""
    cap = np.log1p(float(train.max())) + LOG_CAP
    return np.expm1(np.minimum(np.asarray(z, dtype=float), cap))


class SarimaxForecaster(Forecaster):
    """Wrapper para o modelo SARIMAX de statsmodels."""

    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12), log_target: bool = False):
        self.order = order
        self.seasonal_order = seasonal_order
        self.log_target = log_target
        self.name = _log_name("sarimax", log_target)

    def forecast(self, train: pd.Series, horizon: int) -> np.ndarray:
        y = np.log1p(train) if self.log_target else train
        model = SARIMAX(
            y,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit = model.fit(disp=False)
        pred = fit.forecast(steps=horizon)
        result = np.asarray(pred, dtype=float)
        if self.log_target:
            result = _from_log(result, train)
        return np.maximum(0, result)


class SkforecastWrapper(Forecaster):
    """Wrapper genérico para modelos de ML usando ForecasterRecursive do skforecast."""

    def __init__(self, estimator, lags: int = 24, name: str | None = None, transformer_y=None, log_target: bool = False):
        self.estimator = estimator
        self.lags = lags
        self.log_target = log_target
        base = name or estimator.__class__.__name__.lower().replace("regressor", "")
        self.name = _log_name(base, log_target)
        # Só os estimadores sensíveis a escala precisam disto. As árvores são
        # invariantes a escala e passam None, o que preserva os resultados já
        # publicados delas.
        self.transformer_y = transformer_y

    def forecast(self, train: pd.Series, horizon: int) -> np.ndarray:
        forecaster = ForecasterRecursive(
            estimator=self.estimator, lags=self.lags, transformer_y=self.transformer_y
        )
        y = np.log1p(train) if self.log_target else train
        forecaster.fit(y=y)
        predictions = forecaster.predict(steps=horizon).to_numpy()
        if self.log_target:
            predictions = _from_log(predictions, train)
        return np.maximum(0, predictions)


def lgbm_forecaster(lags: int = 24, log_target: bool = False) -> SkforecastWrapper:
    return SkforecastWrapper(
        estimator=LGBMRegressor(random_state=42, verbosity=-1),
        lags=lags,
        name="lgbm",
        log_target=log_target,
    )


def xgboost_forecaster(lags: int = 24, log_target: bool = False) -> SkforecastWrapper:
    return SkforecastWrapper(
        estimator=XGBRegressor(random_state=42, objective="reg:squarederror"),
        lags=lags,
        name="xgboost",
        log_target=log_target,
    )


def catboost_forecaster(lags: int = 24, log_target: bool = False) -> SkforecastWrapper:
    return SkforecastWrapper(
        estimator=CatBoostRegressor(random_state=42, verbose=0),
        lags=lags,
        name="catboost",
        log_target=log_target,
    )


def randomforest_forecaster(lags: int = 24, log_target: bool = False) -> SkforecastWrapper:
    return SkforecastWrapper(
        estimator=RandomForestRegressor(random_state=42, n_estimators=100),
        lags=lags,
        name="randomforest",
        log_target=log_target,
    )


def ridge_forecaster(lags: int = 24, log_target: bool = False) -> SkforecastWrapper:
    """Ridge sobre lags padronizados.

    O StandardScaler nao e cosmetico. Sem ele a penalidade L2 com alpha=1.0 e
    desprezivel diante de contagens na casa dos milhares, e nos folds iniciais,
    onde o numero de linhas de treino se aproxima do numero de lags, o ajuste
    fica quase singular. A previsao recursiva de 12 passos amplifica isso: em
    Salvador, o fold com 49 meses de treino produzia 8.7e14 casos e sozinho
    contaminava o MAE e o RMSE agregados da cidade. Com padronizacao nenhum
    fold diverge. As arvores nao precisam disto por serem invariantes a escala.
    """
    return SkforecastWrapper(
        estimator=Ridge(random_state=42),
        lags=lags,
        name="ridge",
        log_target=log_target,
        transformer_y=StandardScaler(),
    )


class ProphetForecaster(Forecaster):
    """Wrapper para o Prophet (Meta)."""

    name = "prophet"

    def forecast(self, train: pd.Series, horizon: int) -> np.ndarray:
        from prophet import Prophet  # lazy import

        df = train.reset_index()
        df.columns = ["ds", "y"]
        df["ds"] = pd.to_datetime(df["ds"])

        model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(df)

        future = model.make_future_dataframe(periods=horizon, freq="MS")
        forecast = model.predict(future)
        preds = forecast["yhat"].iloc[-horizon:].to_numpy(dtype=float)
        return np.maximum(0, preds)


class TimesFMForecaster(Forecaster):
    """Wrapper zero-shot para TimesFM 2.5 do Google.

    Modelo de fundação pré-treinado: não requer treinamento.
    O contexto histórico é passado diretamente ao modelo via HuggingFace.
    O modelo é carregado uma única vez e cacheado na classe.
    """

    name = "timesfm"
    _model = None  # cache de classe para evitar recarregamento a cada fold

    def _get_model(self):
        if TimesFMForecaster._model is None:
            if not _TIMESFM_AVAILABLE:
                raise ImportError("timesfm nao instalado. Execute: pip install 'timesfm[torch] @ git+https://github.com/google-research/timesfm.git'")
            model = _timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                "google/timesfm-2.5-200m-pytorch"
            )
            model.compile(
                _timesfm.ForecastConfig(
                    max_context=512,
                    max_horizon=24,
                    normalize_inputs=True,
                    infer_is_positive=True,
                )
            )
            TimesFMForecaster._model = model
        return TimesFMForecaster._model

    def forecast(self, train: pd.Series, horizon: int) -> np.ndarray:
        model = self._get_model()
        context = train.to_numpy(dtype=float)
        point_forecast, _ = model.forecast(horizon=horizon, inputs=[context])
        return np.maximum(0, point_forecast[0])
