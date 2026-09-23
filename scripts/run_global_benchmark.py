"""Backtest dos modelos globais: um modelo por janela, treinado nas 8 cidades juntas.

Mesmo rolling origin dos modelos locais, e de propósito: as 8 séries
compartilham o mesmo índice de datas, então as 119 janelas e os 12 alvos de cada
uma são exatamente os mesmos. É isso que torna a comparação pareada e permite
que o global entre nos CSVs existentes ao lado do local, sem reexecutar nada.

A diferença é que aqui uma janela produz previsão para as 8 cidades ao mesmo
tempo, e um erro em qualquer uma delas descarta a janela inteira para todas: a
janela é a unidade de ajuste, e guardar meia janela produziria um CSV em que
cidades diferentes teriam conjuntos de janelas diferentes, quebrando o
pareamento do bootstrap sem que nada avisasse.

Uso:
  PYTHONPATH=src python scripts/run_global_benchmark.py
  PYTHONPATH=src python scripts/run_global_benchmark.py --models global_ridge --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dengue_forecast.evaluate import mae, rmse, rolling_origin_splits, smape
from dengue_forecast.global_models import build_global_models, to_wide

ROOT = Path(__file__).resolve().parents[1]

CITIES = [
    ("sao", "sao_paulo"),
    ("rio", "rio"),
    ("belo", "belo_horizonte"),
    ("brasilia", "brasilia"),
    ("fortaleza", "fortaleza"),
    ("recife", "recife"),
    ("manaus", "manaus"),
    ("salvador", "salvador"),
]

DEFAULT_MODELS = "global_lgbm,global_xgboost,global_catboost,global_randomforest,global_ridge"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", default=str(ROOT / "data" / "processed"))
    p.add_argument("--results-dir", default=str(ROOT / "results"))
    p.add_argument("--models", default=DEFAULT_MODELS)
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--min-train-size", type=int, default=48)
    p.add_argument("--lags", type=int, default=24)
    p.add_argument(
        "--no-scale-series",
        action="store_true",
        help=(
            "Desliga a padronizacao por serie. Serve so para a analise de "
            "sensibilidade: sem ela o treino conjunto e dominado pelas cidades "
            "grandes. Grava com sufixo _noscale e nao entra nos CSVs principais."
        ),
    )
    p.add_argument("--dry-run", action="store_true", help="Roda e mede, mas nao escreve.")
    return p.parse_args()


def carrega_series(data_dir: Path) -> dict[str, pd.Series]:
    out = {}
    for src, nome in CITIES:
        df = pd.read_csv(data_dir / f"dengue_monthly_{src}.csv", parse_dates=["date"])
        out[nome] = df.set_index("date")["value"].astype(float).sort_index().asfreq("MS")
    return out


def backtest_global(model, wide: pd.DataFrame, horizon: int, min_train_size: int):
    """Devolve (linhas, janelas_descartadas). Uma janela vale para as 8 cidades."""
    splits = list(rolling_origin_splits(wide, horizon=horizon, min_train_size=min_train_size))
    linhas = []
    descartadas: list[int] = []

    for window_id, (train, test) in enumerate(splits, start=1):
        try:
            pred = model.forecast(train, horizon=len(test))
        except Exception as exc:
            print(f"    [WARN] Falha em {model.name} (janela {window_id}): {exc}")
            descartadas.append(window_id)
            continue

        y_pred = pred.to_numpy(dtype=float)
        y_true = test.to_numpy(dtype=float)

        if y_pred.shape != y_true.shape:
            print(
                f"    [WARN] Forma invalida em {model.name} (janela {window_id}): "
                f"pred={y_pred.shape} true={y_true.shape}"
            )
            descartadas.append(window_id)
            continue

        if not np.all(np.isfinite(y_pred)):
            print(
                f"    [WARN] Previsao nao-finita em {model.name} (janela {window_id}); "
                "janela descartada para as 8 cidades"
            )
            descartadas.append(window_id)
            continue

        # Alerta de faixa por cidade, diagnostico e sem clamp, igual ao local.
        for j, cidade in enumerate(wide.columns):
            lo = train[cidade].min() * 0.1
            hi = train[cidade].max() * 3.0
            if np.any((y_pred[:, j] < lo) | (y_pred[:, j] > hi)):
                print(
                    f"    [WARN] {model.name} fora de [{lo:.1f}, {hi:.1f}] em {cidade} "
                    f"(janela {window_id}); valor mantido sem clamp"
                )

        for j, cidade in enumerate(wide.columns):
            for h, dt in enumerate(test.index, start=1):
                linhas.append(
                    {
                        "city": cidade,
                        "model": model.name,
                        "date": dt,
                        "y_true": y_true[h - 1, j],
                        "y_pred": y_pred[h - 1, j],
                        "window": window_id,
                        "horizon": h,
                    }
                )

    return pd.DataFrame(linhas), descartadas, len(splits)


def grava(preds: pd.DataFrame, results_dir: Path, sufixo: str) -> None:
    """Mescla nos CSVs por cidade, substituindo so as linhas dos modelos rodados."""
    rodados = sorted(preds["model"].unique())
    for cidade, sub in preds.groupby("city", sort=False):
        ppath = results_dir / f"benchmark_{cidade}{sufixo}_predictions.csv"
        mpath = results_dir / f"benchmark_{cidade}{sufixo}_metrics.csv"
        novo = sub.drop(columns=["city"]).copy()
        novo["date"] = pd.to_datetime(novo["date"]).dt.strftime("%Y-%m-%d")

        if ppath.exists():
            antigo = pd.read_csv(ppath)
            mantidos = antigo[~antigo["model"].isin(rodados)]
            novo = pd.concat([mantidos, novo], ignore_index=True)
        novo.to_csv(ppath, index=False)

        linhas_met = []
        for m, g in sub.groupby("model", sort=False):
            yt = g["y_true"].to_numpy(float)
            yp = g["y_pred"].to_numpy(float)
            linhas_met.append(
                {
                    "model": m,
                    "mae": mae(yt, yp),
                    "rmse": rmse(yt, yp),
                    "smape": smape(yt, yp),
                    "n_predictions": len(yt),
                }
            )
        met = pd.DataFrame(linhas_met)
        if mpath.exists():
            antigo = pd.read_csv(mpath)
            met = pd.concat([antigo[~antigo["model"].isin(rodados)], met], ignore_index=True)
        met.sort_values("smape").to_csv(mpath, index=False)
        print(f"  [INFO] {ppath.name} e {mpath.name} atualizados")


def main() -> int:
    args = parse_args()
    data_dir = Path(args.data_dir)
    results_dir = Path(args.results_dir)

    series = carrega_series(data_dir)
    wide = to_wide(series)
    print(f"[INFO] {wide.shape[1]} cidades, {wide.shape[0]} meses, {wide.index.min():%Y-%m} a {wide.index.max():%Y-%m}")

    escalar = not args.no_scale_series
    sufixo = "" if escalar else "_noscale"
    if not escalar:
        print("[INFO] Sem padronizacao por serie: rodada de sensibilidade, sufixo _noscale")

    modelos = build_global_models(
        args.models.split(","), lags=args.lags, scale_series=escalar
    )

    todas = []
    incompletos: dict[str, list[int]] = {}
    n_janelas = None

    for model in modelos:
        print(f"  [INFO] Rodando backtest global para: {model.name}")
        preds, descartadas, n_janelas = backtest_global(
            model, wide, args.horizon, args.min_train_size
        )
        if descartadas:
            incompletos[model.name] = descartadas
        if not preds.empty:
            todas.append(preds)
            for cidade, g in preds.groupby("city", sort=False):
                yt = g["y_true"].to_numpy(float)
                yp = g["y_pred"].to_numpy(float)
                print(
                    f"      {cidade:<16} sMAPE {smape(yt, yp):>7.2f}  MAE {mae(yt, yp):>9.1f}  "
                    f"n {len(yt)}"
                )

    if todas and not args.dry_run:
        grava(pd.concat(todas, ignore_index=True), results_dir, sufixo)
    elif args.dry_run:
        print("[DRY-RUN] nada escrito")

    if incompletos:
        print()
        print("[ERRO] Modelos globais com janelas faltando:")
        for nome, janelas in sorted(incompletos.items()):
            amostra = ", ".join(str(j) for j in janelas[:10])
            reticencia = " ..." if len(janelas) > 10 else ""
            print(f"  {nome}: {len(janelas)} de {n_janelas} janelas perdidas ({amostra}{reticencia})")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
