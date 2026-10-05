# PROGRESS: Dengue Forecast Prediction (DFP)

Atualizado em 2026-10-04.

## Decisão de 04/10/2026
Este repositório é o **canônico** do estudo. O `dengue-timeseries-skforecast` (benchmark v2, PLOS) fica arquivado como referência; dele vieram duas correções, portadas aqui. Revista-alvo: **PLOS NTD**. Autores, nesta ordem: Fabiano Novaes Barcellos Filho (USP, correspondente), José Trajano, Wilson Falco e Alexandre Chiavegatto Filho (orientador). Sem financiamento.

## Estado
- Variantes log1p dos modelos treinados (`*_log`), em emenda **exploratória** no `results/criterion.json`, feita depois de ver resultados. Veredito confirmatório inalterado: nenhum modelo bate o naive (0/8). Exploratório: também 0/8; TimesFM contra as variantes log tem 3/48 pares confirmados (todos em Brasília), 0 contra o CatBoost log. RelMAE médio: TimesFM 0,829 e CatBoost log 0,872.
- `run_uncertainty.py` com escopo explícito: confirmatório e exploratório em arquivos separados.
- IC descritivo do sMAPE por janela inteira (B = 10.000, semente do critério), no lugar do bootstrap iid das previsões.
- `build_docx.py`: autoria nova, afiliações de José e Wilson como `[PENDING]`, Métodos e Resultados exploratórios (Tabela 10), "comparable, not better".
- Mac reproduz o Windows (árvores até 1e-12) com torch 2.8.0 e timesfm no commit 8a755c9 (ver requirements-optional.txt).
- LAB-135 (05/10): comentário registrando que o critério de 23/09 (RelMAE, commit 0f7fdd6, fixado 4 min antes da primeira rodada) resolve o bloqueio para a publicação de dengue. A issue já estava Done pelo lado do OPT.

## Próximos passos
1. Coautores revisam `build/manuscript_review.docx` (preenchem as afiliações e revisam o enquadramento exploratório).
2. Decidir se o repositório fica público (ou Zenodo com DOI): a frase de disponibilidade de código depende disso.
3. Incorporar a revisão e atualizar o `.tex` de submissão no template PLOS NTD. Os `.tex` atuais (`manuscript.tex`, `manuscript_rsbmt.tex`, `supplementary.tex`) ainda trazem os ICs antigos (bootstrap iid), "Barcellos-Filho", "Google DeepMind" e a autoria sem Alexandre.
4. Incluir os ICs na lista curada do `check_numbers.py`: hoje ele não detecta IC defasado no texto.
5. Push só com o OK do Fabiano (regra do repo).

## Restrições
- Números só por script (`verified_numbers.json`); push só com OK.
- Rodar no `.venv` (Python 3.12) com os pins; sem eles o LightGBM dá segfault no macOS ARM.
