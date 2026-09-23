# Caminho absoluto de uma maquina so torna o alvo nao executavel em qualquer
# outra. Sobrescreva com `make PYTHON=.venv/Scripts/python.exe` se precisar.
PYTHON ?= python
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

# Pares arquivo:prefixo. O nome do CSV de entrada e o nome do resultado nao
# coincidem em duas cidades (sao/sao_paulo e belo/belo_horizonte), entao
# derivar um do outro com sed criava arquivos novos em vez de regravar os de
# results/, e `make benchmark-all` nao reproduzia o que esta publicado.
CITIES = sao:sao_paulo rio:rio belo:belo_horizonte brasilia:brasilia \
         fortaleza:fortaleza recife:recife manaus:manaus salvador:salvador

benchmark-sp:
	PYTHONPATH=src $(PYTHON) scripts/run_benchmark.py \
		--input-csv data/processed/dengue_monthly_sao.csv \
		--output-prefix results/benchmark_sao_paulo \
		--horizon 12 \
		--min-train-size 48

benchmark-all:
	@echo "Running benchmark for all cities..."
	@for pair in $(CITIES); do \
		src_name=$${pair%%:*}; out_name=$${pair##*:}; \
		echo "--> Running for $$out_name"; \
		PYTHONPATH=src $(PYTHON) scripts/run_benchmark.py \
			--input-csv data/processed/dengue_monthly_$$src_name.csv \
			--output-prefix results/benchmark_$$out_name \
			--horizon 12 \
			--min-train-size 48 || exit 1; \
	done

# --- manuscrito -------------------------------------------------------------
# paper-assets recalcula toda tabela e figura dos dados brutos. Rode sempre
# antes de compilar: as tabelas em paper/tables/ sao geradas, nao editadas.
paper-assets:
	$(PYTHON) scripts/build_paper_assets.py

paper: paper-assets
	mkdir -p build
	cd paper && $(TECTONIC) -X compile manuscript.tex --outdir ../build
	@echo "PDF em build/manuscript.pdf"

paper-clean:
	rm -rf build paper/tables paper/figures paper/verified_numbers.json

# versao condensada para a Rev Soc Bras Med Trop, mais o suplementar
paper-rsbmt: paper-assets
	mkdir -p build
	cd paper && $(TECTONIC) -X compile manuscript_rsbmt.tex --outdir ../build
	cd paper && $(TECTONIC) -X compile supplementary.tex --outdir ../build
	$(PYTHON) scripts/check_limits.py manuscript_rsbmt.tex
