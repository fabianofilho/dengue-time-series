# Campos do Editorial Manager (PLOS NTD)

A PLOS pede estes itens nos campos do sistema de submissão, não no arquivo do manuscrito
(funding não pode aparecer no manuscrito). Textos prontos para colar. Regras conferidas nas
páginas da PLOS NTD em 09/10/2026 (submission-guidelines, figures, latex,
supporting-information, data-availability).

**Article type**
Research Article

**Full title** (sentence case, até 250 caracteres)
Zero-shot foundation model versus purpose-trained models for dengue forecasting in eight Brazilian state capitals: A rolling-origin benchmark against a seasonal naive baseline

**Short title** (até 70 caracteres)
Zero-shot dengue forecasting in eight Brazilian capitals

**Corresponding author**
Fabiano Novaes Barcellos Filho, fabiano.filho@usp.br, ORCID 0000-0002-1491-2700 (a PLOS exige o ORCID do autor correspondente na submissão).

**Financial Disclosure**
The authors received no specific funding for this work.

**Competing Interests**
The authors have declared that no competing interests exist.

**Data Availability Statement**
All data are publicly available. Monthly dengue case counts were obtained from the InfoDengue public API (https://info.dengue.mat.br/api/). The processed series, all model forecasts, result files, the pre-registered decision rule and the code that reproduces every table, figure and number in the manuscript are available at https://github.com/fabianofilho/dengue-time-series and will be archived at Zenodo with a DOI.

> A PLOS exige o conjunto mínimo de dados público até a publicação, em repositório com DOI ou
> accession, com licença no máximo tão restritiva quanto CC BY. Antes de submeter: abrir o
> repositório; o DOI do Zenodo entra aqui assim que gerado (pode ser atualizado depois).

**Ethics statement**
Not applicable: publicly available, aggregated surveillance data with no individual-level information (CNS Resolution 510/2016, Article 1, items II and V). The full statement is in the Methods.

**Author Contributions (CRediT)**
**Fabiano Novaes Barcellos Filho:** Conceptualization, Data curation, Formal analysis, Investigation, Methodology, Project administration, Software, Validation, Visualization, Writing: original draft, Writing: review and editing.
**José Trajano Feitosa Filho:** Conceptualization, Formal analysis, Methodology, Supervision, Writing: review and editing.
**Wilson Falco:** Data curation, Investigation, Software, Writing: review and editing.
**Alexandre Chiavegatto Filho:** Supervision, Writing: review and editing.
All authors read and approved the final manuscript.

> Conferir com o José, o Wilson e o Alexandre antes de submeter. O Alexandre aparece só com
> Supervision e revisão; se ele contribuiu com Conceptualization ou Methodology, acrescentar.

## Arquivos a enviar

Todos gerados por `python scripts/build_plos.py` (rodar antes `PYTHONPATH=src python scripts/build_paper_assets.py` se os resultados mudaram).

| Arquivo | Onde está | Tipo no Editorial Manager |
|---|---|---|
| Manuscrito (PDF, sem figuras, com legendas, tabelas e referências) | `build/plos/manuscript.pdf` | Manuscript |
| Fig1.tif a Fig10.tif (TIFF, 300 dpi, RGB, largura até 2250 px) | `build/plos/figures/` | Figure |
| Cover letter | `paper/submission/cover_letter.md` | Cover Letter |
| Fonte LaTeX em arquivo único | `build/plos/manuscript.tex` | só depois do aceite |

A PLOS não aceita figura dentro do PDF do manuscrito: as legendas ficam no texto, logo após o
parágrafo que cita a figura pela primeira vez, e os TIFF sobem separados.

## Taxa de publicação

Não conferida na fonte: as páginas de taxa da PLOS recusaram acesso automatizado em 09/10/2026.
Um resumo de busca e o DOAJ indicam US$ 2.670 para Research Article na PLOS NTD. Conferir o
valor e o programa PLOS Fee Assistance no navegador antes de submeter.
