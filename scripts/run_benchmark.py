"""
Executa o benchmark de backtesting para múltiplos modelos de forecasting em um dataset de série temporal de dengue.

Exemplo de uso:
  python scripts/run_benchmark.py \
    --input-csv data/processed/dengue_monthly_sao_paulo.csv \
    --output-prefix results/benchmark_sao_paulo
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from dengue_forecast.evaluate import rolling_origin_splits, run_backtest
from dengue_forecast.models import (
    ProphetForecaster,
    SarimaxForecaster,
    SeasonalNaiveForecaster,
    TimesFMForecaster,
    catboost_forecaster,
    lgbm_forecaster,
    randomforest_forecaster,
    ridge_forecaster,
    xgboost_forecaster,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark de modelos de forecasting de dengue")
    parser.add_argument("--input-csv", required=True, help="CSV com a série temporal mensal")
    parser.add_argument("--date-col", default="date", help="Nome da coluna de data")
    parser.add_argument("--value-col", default="value", help="Nome da coluna de valor (casos)")
    parser.add_argument("--horizon", type=int, default=12, help="Horizonte de previsão (meses)")
    parser.add_argument("--min-train-size", type=int, default=48, help="Janela mínima de treino (meses)")
    parser.add_argument(
        "--models",
        default="seasonal_naive,sarimax,lgbm,xgboost,catboost,randomforest,ridge,timesfm",
        help=(
            "Lista de modelos para rodar (separados por vírgula). O default é o "
            "conjunto de 7 modelos publicado mais o naive sazonal. Prophet "
            "continua disponível por nome, "
            "mas exige requirements-optional.txt instalado."
        ),
    )
    parser.add_argument("--output-prefix", required=True, help="Prefixo para os arquivos de saída")
    parser.add_argument("--lags", type=int, default=24, help="Número de lags para modelos de ML")
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "Mescla nos CSVs existentes em vez de sobrescrever. As linhas dos modelos "
            "rodados agora substituem as antigas; os demais modelos ficam intactos. "
            "Use para acrescentar um modelo sem reexecutar os caros (TimesFM)."
        ),
    )
    return parser.parse_args()


def build_models(model_names: list[str], lags: int):
    """Constrói a lista de objetos de modelo com base nos nomes fornecidos."""
    selected = {m.strip().lower() for m in model_names if m.strip()}
    valid = {
        "seasonal_naive",
        "sarimax",
        "prophet",
        "lgbm",
        "xgboost",
        "catboost",
        "randomforest",
        "ridge",
        "timesfm",
    }
    invalid = selected - valid
    if invalid:
        raise ValueError(f"Modelos inválidos: {sorted(invalid)}")

    models = []
    if "seasonal_naive" in selected:
        models.append(SeasonalNaiveForecaster())
    if "sarimax" in selected:
        models.append(SarimaxForecaster(order=(1, 1, 1), seasonal_order=(1, 1, 0, 12)))
    if "prophet" in selected:
        models.append(ProphetForecaster())
    if "lgbm" in selected:
        models.append(lgbm_forecaster(lags=lags))
    if "xgboost" in selected:
        models.append(xgboost_forecaster(lags=lags))
    if "catboost" in selected:
        models.append(catboost_forecaster(lags=lags))
    if "randomforest" in selected:
        models.append(randomforest_forecaster(lags=lags))
    if "ridge" in selected:
        models.append(ridge_forecaster(lags=lags))
    if "timesfm" in selected:
        models.append(TimesFMForecaster())

    if not models:
        raise ValueError("Nenhum modelo válido selecionado.")
    return models


def main() -> None:
    args = parse_args()

    # Carrega e prepara a série temporal
    series = pd.read_csv(
        args.input_csv,
        index_col=args.date_col,
        parse_dates=[args.date_col],
    )[args.value_col].asfreq("MS")

    models = build_models(args.models.split(","), lags=args.lags)

    n_folds = sum(
        1
        for _ in rolling_origin_splits(
            series, horizon=args.horizon, min_train_size=args.min_train_size
        )
    )

    metrics_rows = []
    preds_frames = []
    incompletos: dict[str, list[int]] = {}

    print(f"[INFO] Iniciando benchmark para {args.input_csv} ({n_folds} janelas)...")
    for model in models:
        metric_row, pred_df, skipped = run_backtest(
            series=series,
            model=model,
            horizon=args.horizon,
            min_train_size=args.min_train_size,
        )
        if skipped:
            incompletos[model.name] = skipped
        if metric_row is not None:
            metrics_rows.append(metric_row)
        if not pred_df.empty:
            preds_frames.append(pred_df)

    # Salva os resultados
    output_prefix = Path(args.output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)

    ran = [m.name for m in models]

    def merge(new_df: pd.DataFrame, path: Path) -> pd.DataFrame:
        """Substitui as linhas dos modelos rodados agora, preserva as demais."""
        if not (args.append and path.exists()):
            return new_df
        old = pd.read_csv(path)
        kept = old[~old["model"].isin(ran)]
        print(f"[INFO] Append em {path.name}: mantendo {sorted(kept['model'].unique())}")
        return pd.concat([kept, new_df], ignore_index=True)

    if metrics_rows:
        metrics_path = output_prefix.with_name(output_prefix.name + "_metrics.csv")
        metrics_df = merge(pd.DataFrame(metrics_rows), metrics_path)
        metrics_df = metrics_df.sort_values(by="smape")
        metrics_df.to_csv(metrics_path, index=False)
        print(f"\n[INFO] Métricas salvas em: {metrics_path}")
        print(metrics_df)

    if preds_frames:
        preds_path = output_prefix.with_name(output_prefix.name + "_predictions.csv")
        preds_df = merge(pd.concat(preds_frames, ignore_index=True), preds_path)
        # Normaliza para ISO sem hora. Sem isto o --append mistura formatos:
        # as linhas novas saem como "2014-01-01 00:00:00" e as antigas como
        # "2014-01-01", e quem for parsear a coluna depois quebra.
        preds_df["date"] = pd.to_datetime(preds_df["date"]).dt.strftime("%Y-%m-%d")
        preds_df.to_csv(preds_path, index=False)
        print(f"[INFO] Previsões salvas em: {preds_path}")

    # A execução só termina em sucesso se todo modelo cobriu todas as janelas.
    # Sem isto um modelo pode sumir do CSV sem que nada falhe, que foi
    # exatamente o que aconteceu com o Prophet: ele estava no default, não
    # estava instalado, e o benchmark terminou com código zero mesmo assim.
    if incompletos:
        print()
        print("[ERRO] Modelos com janelas faltando:")
        for nome, janelas in sorted(incompletos.items()):
            faltando = len(janelas)
            amostra = ", ".join(str(j) for j in janelas[:10])
            reticencia = " ..." if faltando > 10 else ""
            print(f"  {nome}: {faltando} de {n_folds} janelas perdidas ({amostra}{reticencia})")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
