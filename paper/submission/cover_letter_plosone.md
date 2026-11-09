Dear Editors,

We are transferring our manuscript "Zero-shot foundation model versus purpose-trained models for dengue forecasting in eight Brazilian state capitals: A rolling-origin benchmark against a seasonal naive baseline" to PLOS ONE as a Research Article, following the transfer offer from PLOS Neglected Tropical Diseases (PNTD-D-26-02067). The editors there did not consider it for publication in that journal and suggested PLOS ONE.

Why the manuscript is suitable for PLOS ONE. The study meets the journal's criteria on scientific rigor rather than on perceived novelty. It is a pre-specified, fully reproducible benchmark. We evaluated 79,968 forecasts by rolling-origin cross-validation in eight Brazilian state capitals over fifteen years, and we fixed the decision rule for beating a seasonal naive forecast in the project repository before running the comparison; the order of the commits is public. The conclusions follow from the data: under that rule no model, including the foundation model TimesFM 2.5 and five models pooled across cities, beat the seasonal naive forecast in any city. The best model's mean absolute error relative to the naive forecast ranged from 0.665 to 0.961, but the improvement was not consistent across forecast horizons. The exploratory comparison among models is labelled as exploratory, and we do not present the ranking as evidence for deployment.

What the paper adds to the literature. Dengue forecasting studies often compare models with each other and not with a simple seasonal benchmark, which makes a ranking look more useful than it is. Our paper shows, with a decision rule fixed in advance, that a ranking among forecasting models can be compatible with none of them being useful. It also shows that a single pre-trained model, with no local training, was comparable to the best city-trained models (mean relative error 0.829 against 0.872 for CatBoost fitted on log counts), which matters for municipalities without modelling capacity. We recommend that dengue forecasting studies report a seasonal naive benchmark and a decision rule fixed in advance, and we provide the code to do so.

How it relates to previously published work. The manuscript addresses dengue forecasting in Brazil and the evaluation of time-series foundation models, and it relates its results to previously published work in the Introduction and the Discussion.

Who will be most interested. Infectious disease modellers and forecasters, public health epidemiologists and vector-control planners working with arbovirus surveillance, and machine learning researchers who evaluate foundation models on real surveillance data.

All data are public (InfoDengue), and the code that regenerates every table, figure and number in the manuscript is available in the project repository and will be archived with a DOI. The manuscript is not under consideration elsewhere, all authors have approved it, and the authors declare no competing interests. The study received no specific funding.

Sincerely,

Fabiano Novaes Barcellos Filho, on behalf of all authors
Laboratório de Big Data e Análise Preditiva em Saúde (LABDAPS), Faculdade de Saúde Pública, Universidade de São Paulo
fabiano.filho@usp.br, ORCID 0000-0002-1491-2700
