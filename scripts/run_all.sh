#!/usr/bin/env bash
# Reexecuta o benchmark completo das 8 capitais sobre a serie corrigida.
#
# 7 modelos, sem prophet, que falha em 7 das 8 cidades por dependencia.
# Sobrescreve results/benchmark_*: o estado anterior esta em archive_v1/.
#
# Uso:  PY=.venv/Scripts/python.exe bash scripts/run_all.sh
set -u
PY="${PY:-python}"
MODELS="${MODELS:-sarimax,lgbm,xgboost,catboost,randomforest,ridge,timesfm}"

pairs="sao:sao_paulo rio:rio belo:belo_horizonte brasilia:brasilia \
fortaleza:fortaleza recife:recife manaus:manaus salvador:salvador"

start=$(date +%s)
for pair in $pairs; do
  src="${pair%%:*}"; dst="${pair##*:}"
  echo "=== $dst  ($(( $(date +%s) - start ))s decorridos) ==="
  PYTHONPATH=src "$PY" -W ignore scripts/run_benchmark.py \
    --input-csv "data/processed/dengue_monthly_${src}.csv" \
    --output-prefix "results/benchmark_${dst}" \
    --models "$MODELS" \
    --horizon 12 --min-train-size 48 2>&1 \
  | grep -E "^\s+\[INFO\] Rodando|^\s+\[WARN\]|^[0-9]+\s+\w" || true
done
echo "=== concluido em $(( $(date +%s) - start ))s ==="
