"""Reconstrói as colunas window e horizon nos CSVs de previsão já publicados.

Por que reconstruir em vez de reexecutar: o TimesFM custa horas e os números dos
sete modelos publicados não podem mudar nesta operação. A reconstrução é por
fatiamento determinístico, 12 linhas por janela na ordem do arquivo, exatamente
a estrutura que run_backtest grava.

O ponto que faz isto ser verificação e não suposição: a sequência de datas
resultante é comparada com a que rolling_origin_splits produz a partir da série
de origem. Se um único alvo estiver fora de lugar, o modelo é reprovado, fica
sem as colunas e é listado para reexecução. Nada é escrito por palpite.

Uso:
  python scripts/backfill_windows.py                # todas as cidades
  python scripts/backfill_windows.py --dry-run      # só relata, não escreve
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from dengue_forecast.evaluate import rolling_origin_splits

# Mesmos pares do Makefile: o nome do CSV de entrada e o do resultado não
# coincidem em duas cidades.
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", default="data/processed")
    p.add_argument("--results-dir", default="results")
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--min-train-size", type=int, default=48)
    p.add_argument("--dry-run", action="store_true", help="Relata sem escrever.")
    return p.parse_args()


def expected_dates(series: pd.Series, horizon: int, min_train_size: int) -> pd.DataFrame:
    """Uma linha por (janela, passo) com a data alvo que o backtest teria gravado."""
    linhas = []
    splits = rolling_origin_splits(series, horizon=horizon, min_train_size=min_train_size)
    for window_id, (_train, test) in enumerate(splits, start=1):
        for h, dt in enumerate(test.index, start=1):
            linhas.append({"window": window_id, "horizon": h, "date": dt})
    return pd.DataFrame(linhas)


def backfill_city(
    series_path: Path, preds_path: Path, horizon: int, min_train_size: int, dry_run: bool
) -> list[str]:
    """Devolve a lista de modelos que falharam a validação."""
    series = pd.read_csv(series_path, index_col="date", parse_dates=["date"])["value"].asfreq("MS")
    esperado = expected_dates(series, horizon, min_train_size)
    n_alvos = len(esperado)

    preds = pd.read_csv(preds_path)
    preds["date"] = pd.to_datetime(preds["date"])

    reprovados: list[str] = []
    partes = []

    for model, sub in preds.groupby("model", sort=False):
        s = sub.reset_index(drop=True).copy()
        motivo = None

        if len(s) != n_alvos:
            motivo = f"{len(s)} linhas, esperado {n_alvos}"
        else:
            s["window"] = esperado["window"].to_numpy()
            s["horizon"] = esperado["horizon"].to_numpy()
            if not (s["date"].to_numpy() == esperado["date"].to_numpy()).all():
                fora = int((s["date"].to_numpy() != esperado["date"].to_numpy()).sum())
                motivo = f"{fora} alvos com data fora do lugar"
                s = s.drop(columns=["window", "horizon"])

        if motivo is not None:
            print(f"    [FALHA] {model}: {motivo}")
            reprovados.append(model)
        else:
            print(f"    [OK] {model}: {n_alvos} alvos em {esperado['window'].max()} janelas")

        partes.append(s)

    if reprovados:
        print(f"    [ERRO] {preds_path.name} nao foi reescrito: {sorted(reprovados)} reprovaram")
        return reprovados

    saida = pd.concat(partes, ignore_index=True)
    saida["date"] = saida["date"].dt.strftime("%Y-%m-%d")
    saida = saida[["model", "date", "y_true", "y_pred", "window", "horizon"]]
    if dry_run:
        print(f"    [DRY-RUN] escreveria {len(saida)} linhas em {preds_path.name}")
    else:
        saida.to_csv(preds_path, index=False)
        print(f"    [INFO] {preds_path.name} reescrito com window e horizon")
    return []


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    results_dir = Path(args.results_dir)

    falhas: dict[str, list[str]] = {}
    for src_name, out_name in CITIES:
        series_path = data_dir / f"dengue_monthly_{src_name}.csv"
        preds_path = results_dir / f"benchmark_{out_name}_predictions.csv"
        print(f"[INFO] {out_name}")
        reprovados = backfill_city(
            series_path, preds_path, args.horizon, args.min_train_size, args.dry_run
        )
        if reprovados:
            falhas[out_name] = reprovados

    if falhas:
        print()
        print("[ERRO] Reexecute estes pares cidade/modelo antes de seguir:")
        for cidade, modelos in sorted(falhas.items()):
            print(f"  {cidade}: {', '.join(sorted(modelos))}")
        sys.exit(1)

    print()
    print("[INFO] Todas as cidades validadas contra rolling_origin_splits.")


if __name__ == "__main__":
    main()
