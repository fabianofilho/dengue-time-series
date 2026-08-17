PYTHON ?= /opt/miniconda3/envs/dsc/bin/python
UV ?= $(HOME)/.local/bin/uv

TECTONIC ?= tectonic

.PHONY: setup fetch-data process-data benchmark-all benchmark-sp \
        paper-assets paper paper-clean

setup:
	$(UV) pip install --python $(PYTHON) -r requirements.txt
	$(UV) pip install --python $(PYTHON) "timesfm[torch] @ git+https://github.com/google-research/timesfm.git"

fetch-data:
	$(PYTHON) scripts/fetch_infodengue.py --output-dir data/raw

process-data: fetch-data
	$(PYTHON) scripts/process_data.py --input-dir data/raw --output-dir data/processed

benchmark-sp:
	PYTHONPATH=src $(PYTHON) scripts/run_benchmark.py \
		--input-csv data/processed/dengue_monthly_sao.csv \
		--output-prefix results/benchmark_sao_paulo \
		--horizon 12 \
		--min-train-size 48

benchmark-all:
	@echo "Running benchmark for all cities..."
	@for city_csv in data/processed/dengue_monthly_*.csv; do \
		city_name=$$(basename $$city_csv .csv | sed 's/dengue_monthly_//'); \
		echo "--> Running for $$city_name"; \
		PYTHONPATH=src $(PYTHON) scripts/run_benchmark.py \
			--input-csv $$city_csv \
			--output-prefix results/benchmark_$$city_name \
			--horizon 12 \
			--min-train-size 48; \
	done

# --- manuscrito -------------------------------------------------------------
# paper-assets recalcula toda tabela e figura dos dados brutos. Rode sempre
# antes de compilar: as tabelas em paper/tables/ sao geradas, nao editadas.
paper-assets:
	$(PYTHON) scripts/build_paper_assets.py

paper: paper-assets
	cd paper && $(TECTONIC) -X compile manuscript.tex --outdir ../build
	@echo "PDF em build/manuscript.pdf"

paper-clean:
	rm -rf build paper/tables paper/figures paper/verified_numbers.json
