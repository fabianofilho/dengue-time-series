# Cover letter (PLOS Neglected Tropical Diseases)

> Os números abaixo repetem o manuscrito e são conferidos por `scripts/check_numbers.py`.
> Antes de enviar: confirmar que todos os autores aprovaram a versão final.

Dear Editors,

We submit our manuscript "Zero-shot foundation model versus purpose-trained models for dengue forecasting in eight Brazilian state capitals: A rolling-origin benchmark against a seasonal naive baseline" for consideration as a Research Article in PLOS Neglected Tropical Diseases.

Dengue is the most important arboviral disease in Brazil, and 2024 brought the largest epidemic on record. Municipal forecasts of monthly case counts support the planning of vector control, supplies and hospital capacity, but the models in use must be trained and maintained city by city, which limits how many of Brazil's municipalities can have them. Time-series foundation models forecast a new series without being trained on it, and could remove that burden. We tested whether one of them, TimesFM 2.5, forecasts monthly notified dengue as well as six models trained on each city, and, more fundamentally, whether any of these models improves on a seasonal naive forecast that repeats the same month of the previous year.

The design is what we believe makes the work useful to the journal's readers. We evaluated 79,968 forecasts by rolling-origin cross-validation in eight state capitals over fifteen years, and we fixed the decision rule for beating the seasonal naive forecast in the project repository before running the comparison; the order of the commits is public. Under that rule no model, including the foundation model and five models pooled across cities, beat the seasonal naive forecast in any city: the best model's mean absolute error relative to the naive forecast ranged from 0.665 to 0.961, but the improvement was not consistent across forecast horizons. Within the model comparison, the foundation model was comparable to the best city-trained models without any local training (mean relative error 0.829 against 0.872 for CatBoost fitted on log counts, in an exploratory analysis we label as such). We report these results without presenting the model ranking as evidence for deployment.

We think the findings matter for dengue control and policy in two ways. First, a single pre-trained model performing on par with per-city pipelines lowers the cost of extending forecasting to municipalities without modelling capacity. Second, and more broadly, a ranking among forecasting models is compatible with none of them being useful; we recommend that dengue forecasting studies report a seasonal naive benchmark and a decision rule fixed in advance, and we provide the code to do so.

All data are public (InfoDengue), and the code that regenerates every table, figure and number in the manuscript will be openly available with a DOI. The manuscript is not under consideration elsewhere, all authors have approved it, and the authors declare no competing interests. The study received no specific funding.

Sincerely,

Fabiano Novaes Barcellos Filho, on behalf of all authors
Laboratório de Big Data e Análise Preditiva em Saúde (LABDAPS), Faculdade de Saúde Pública, Universidade de São Paulo
fabiano.filho@usp.br, ORCID 0000-0002-1491-2700
