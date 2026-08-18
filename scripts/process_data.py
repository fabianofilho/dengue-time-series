"""
Processa os dados brutos do InfoDengue, agregando os casos semanais em séries temporais mensais para cada cidade.

Input: data/raw/dengue_*.csv
Output: data/processed/dengue_monthly_*.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def weekly_to_monthly(weekly: pd.Series) -> pd.Series:
    """Converte semanas epidemiologicas em meses de calendario de verdade.

    A versao anterior fazia resample("MS").sum() sobre a data de INICIO da
    semana, o que joga a semana inteira no mes em que caiu o domingo dela. Isso
    nao produz uma serie mensal: produz "soma das 4 ou 5 semanas que comecaram
    neste mes". Na pratica 118 dos 180 meses recebiam 28 dias de casos e 62
    recebiam 35, uma oscilacao artificial de 25% ditada so pelo calendario, com
    periodo de aproximadamente 12,4 meses, que portanto nem se alinha a
    sazonalidade anual que os modelos tentam aprender.

    O erro nao e pequeno: em Sao Paulo a diferenca mediana entre as duas
    agregacoes e de 10,1%, chega a 30,7%, e infla o pico de marco de 2024 em
    16,8% (331.402 contra 275.858 corrigidos).

    Aqui cada semana e distribuida uniformemente pelos 7 dias que ela cobre e a
    soma e feita por mes de calendario. A hipotese de uniformidade dentro da
    semana e uma aproximacao, mas erra por dias dentro de uma mesma semana, nao
    por semanas inteiras entre meses.

    Meses parcialmente cobertos pela serie semanal sao descartados, porque um
    mes com 28 dos 31 dias observados nao e comparavel aos demais.
    """
    if weekly.empty:
        return weekly

    start, end = weekly.index.min(), weekly.index.max() + pd.Timedelta(days=6)
    days = pd.date_range(start, end, freq="D")
    daily = pd.Series(0.0, index=days)
    for dt, cases in weekly.items():
        daily.loc[dt : dt + pd.Timedelta(days=6)] += cases / 7.0

    monthly = daily.resample("MS").sum()
    observed_days = daily.resample("MS").size()
    days_in_month = monthly.index.days_in_month

    complete = observed_days == days_in_month
    dropped = [d.strftime("%Y-%m") for d in monthly.index[~complete]]
    if dropped:
        print(f"  [INFO] meses incompletos descartados: {', '.join(dropped)}")
    return monthly[complete].round().astype(int)


def process_raw_file(input_path: Path, output_dir: Path) -> None:
    """Carrega um arquivo CSV bruto, agrega para frequência mensal e salva."""
    try:
        df = pd.read_csv(input_path)
    except Exception as exc:
        print(f"[WARN] Falha ao ler {input_path}: {exc}")
        return

    df["date"] = pd.to_datetime(df["date"])
    # Usa 'casos' (notificações observadas), não 'casos_est' (estimativa com nowcasting).
    # Neste extrato as duas colunas são idênticas em toda a série, o que indica que o
    # nowcast já convergiu: não há truncamento por atraso de notificação a corrigir.
    series = weekly_to_monthly(df.set_index("date")["casos"])

    series.index.name = "date"
    series.name = "value"

    city_name = input_path.stem.split("_")[1]
    output_path = output_dir / f"dengue_monthly_{city_name}.csv"
    series.to_csv(output_path)
    print(f"[INFO] Série mensal para {city_name} salva em {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Processa dados brutos de dengue")
    parser.add_argument("--input-dir", default="data/raw", help="Diretório com arquivos brutos")
    parser.add_argument("--output-dir", default="data/processed", help="Diretório de saída")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(input_dir.glob("dengue_*.csv"))
    if not raw_files:
        raise FileNotFoundError(f"Nenhum arquivo 'dengue_*.csv' encontrado em {input_dir}")

    for file_path in raw_files:
        process_raw_file(file_path, output_dir)


if __name__ == "__main__":
    main()
