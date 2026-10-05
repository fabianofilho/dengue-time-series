# PROGRESS: Dengue Forecast Prediction (DFP)

Atualizado em 2026-10-05, ao fim da sessão de 04-05/10.

## Objetivo
Artigo comparando o TimesFM 2.5 zero-shot com modelos treinados por cidade na previsão mensal de dengue em 8 capitais, horizonte de 12 meses, para a **PLOS Neglected Tropical Diseases**.

## Decisões de 04/10/2026 e por quê
- **Este repositório é o canônico.** O `fabianofilho/dengue-timeseries-skforecast` (benchmark v2 e LaTeX PLOS, tag `paper-v2`) fica arquivado. Os dois repositórios eram rascunhos do mesmo estudo com conclusões diferentes, e submeter os dois seria publicação duplicada. Da v2 vieram duas correções, portadas para cá.
- **Revista-alvo: PLOS NTD** (antes era RSBMT; a versão RSBMT fica como histórico).
- **Autores, nesta ordem:** Fabiano Novaes Barcellos Filho (LABDAPS/FSP/USP, correspondente, fabiano.filho@usp.br, ORCID 0000-0002-1491-2700), José Trajano, Wilson Falco e Alexandre Chiavegatto Filho (LABDAPS/FSP/USP, orientador). **Sem financiamento.** As afiliações de José e Wilson eles mesmos preenchem no .docx; nunca inventar.
- **Variantes log1p como emenda EXPLORATÓRIA** em `results/criterion.json`: foi decidida depois de ver resultados (os da v2), então não substitui o veredito confirmatório e o texto tem que dizer isso.
- **IC do sMAPE por janela inteira** (mesmo sorteio do critério, B = 10.000), no lugar do bootstrap iid das 1.428 previsões, que saía estreito demais.

## Estado
- Confirmatório (critério de 23/09, RelMAE, inalterado): nenhum modelo bate o seasonal naive, 0 de 8 cidades. A sensibilidade em sMAPE concorda.
- Exploratório (log1p): também 0 de 8. RelMAE médio: TimesFM 0,829; CatBoost log 0,872 (1,134 na escala bruta). TimesFM tem o menor valor pontual em 5 de 8, mas contra as variantes log só 3 de 48 pares são confirmados (todos em Brasília), 0 contra o CatBoost log. Leitura: TimesFM comparável aos melhores treinados, não superior.
- `run_uncertainty.py` com escopo explícito: confirmatório e exploratório (`*_exploratorio_log*`) em arquivos separados; o confirmatório reproduz o commitado (ruído < 1e-11 entre Mac e Windows).
- `build_docx.py` gera o .docx de revisão com a autoria nova, `[PENDING]` nas afiliações de José e Wilson, Métodos e Resultados exploratórios (Tabela 10) e "comparable, not better". Cópia no Drive: `Labs/Dengue Time Series/DFP_manuscrito_revisao_coautores_2026-10-04.docx` (id 1BXD-CfJP197kYml5GUrl74OrJRmElaOY), como .docx (não convertido em Google Doc).
- Documentação do projeto no Drive (Google Doc 1iJsELmCIHUxL5WLn2fRol_Lhf45yq1xtoCmrKRYbQbQ) atualizada em 05/10.
- LAB-135 (05/10): comentário registrando que o critério de 23/09 (commit 0f7fdd6, fixado 4 min antes da primeira rodada) resolve o bloqueio para a publicação de dengue. A issue já estava Done pelo lado do OPT.
- Tudo no `main` remoto.

## Próximos passos
1. Esperar a revisão dos coautores no .docx (afiliações e enquadramento da análise exploratória).
2. Ao voltar o .docx: passar as afiliações para `AFFILIATIONS` em `scripts/build_docx.py` e para o `.tex`, e incorporar os comentários.
3. Decidir sobre o repositório privado: abrir ou depositar no Zenodo com DOI. A frase de disponibilidade de código depende disso.
4. Atualizar o manuscrito de submissão no template LaTeX da PLOS NTD (template oficial v3.8, `plos2025.bst`; a conversão já feita no repo arquivado em `paper/plos/` serve de modelo). Os `.tex` atuais deste repo (`manuscript.tex`, `manuscript_rsbmt.tex`, `supplementary.tex`) ainda trazem os ICs antigos (bootstrap iid), "Barcellos-Filho", "Google DeepMind", autoria sem Alexandre e nada da análise exploratória.
5. Incluir os ICs na lista curada do `scripts/check_numbers.py`: hoje ele não detecta IC defasado no texto.
6. Opcional: renderizar o .docx em PDF para conferência visual (só houve validação estrutural; a exportação pelo Word foi cancelada).

## Restrições
- Números só por script (`paper/verified_numbers.json`, `build_paper_assets.py`); nada digitado.
- Commit local por etapa; **push só com OK do Fabiano**.
- Ambiente: `.venv` com Python 3.12, os pins de `requirements.txt` e, para o TimesFM, `torch==2.8.0` + timesfm no commit `8a755c9` (`requirements-optional.txt`). Com torch 2.14 e timesfm 3.x o LightGBM dá segfault no macOS ARM.
- Toda contagem "por cidade" depende de quais modelos estão no CSV: o conjunto confirmatório é o de `criterion.json`, nunca o CSV inteiro.

## Descartado
- Afirmar superioridade do TimesFM ("7 de 8"): depende do conjunto comparado e não sobrevive aos modelos treinados em log.
- Submeter o manuscrito do repo `dengue-timeseries-skforecast`.
- RSBMT como revista-alvo.
