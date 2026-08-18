# Cover letter, Revista da Sociedade Brasileira de Medicina Tropical

Dr. Dalmo Correia Filho
Editor-in-Chief
Revista da Sociedade Brasileira de Medicina Tropical

Dear Dr. Correia Filho,

We submit for consideration as an Original Article the manuscript "Zero-Shot Foundation
Models Versus Purpose-Trained Models for Dengue Forecasting in Eight Brazilian State
Capitals (2010 to 2024): A Rolling-Origin Benchmark".

Brazil has the surveillance infrastructure for municipal dengue forecasting but not a
forecasting layer that scales to it, because the models that perform best must be trained
and retrained city by city. That is tractable for 27 federative units and not for 5,570
municipalities. We asked whether a pre-trained time-series foundation model, applied with
no local training at all, can substitute for that per-city pipeline.

Benchmarking seven models on monthly InfoDengue counts for eight capitals under a single
rolling-origin design (119 folds per city, 79,968 predictions), we found that TimesFM 2.5
achieved the lowest sMAPE in seven of eight cities, averaging 74.6% against 85.0% for
CatBoost, the best purpose-trained competitor, despite never seeing the city-specific
training data its competitors were refitted on at every fold. The operational implication
is about cost: the best supervised model is a different model in each city, so a national
programme would need per-city selection and monitoring, whereas one unmodified foundation
model would not.

We want to be explicit about what this manuscript does not claim, because 2025 and 2026
have been productive years for this question in Brazil. Comparative machine learning
evaluation across Brazilian capitals now exists at four-week horizons with climatic and
socioeconomic covariates, Bayesian probabilistic epidemic bands now exist for 118 health
districts, and a prospective multi-team forecasting challenge has been run across five
states. We cite all three and position against them in the Discussion rather than around
them. What remains open, and what this manuscript addresses, is narrower: a 12-month
horizon suited to annual planning rather than outbreak response, a deliberate absence of
covariates so that forecasting architectures are compared on equal information, the first
evaluation of a zero-shot foundation model on Brazilian dengue that we are aware of, and
an audit of whether stated interval coverage actually holds.

That audit produced the results we consider most useful to your readership, and all three
qualify the headline rather than support it. The three accuracy metrics select different
models in half the cities, and in two of them each metric names a different winner, so a
single-metric benchmark would have reached a different conclusion. Conformal prediction
intervals were close to calibrated across the study period but coverage fell to 69.2%
during the 2024 epidemic, meaning the intervals fail precisely when a surveillance system
would rely on them. Combining the models did not beat the best single model in seven of
eight cities. Taken together these argue against deploying any single model on the
strength of a benchmark, and they converge with the conclusion of the 2024 Dengue
Forecasting Sprint, reached prospectively and at state level with covariates, that no
model excelled consistently and that 2024 defeated every approach. Two independent
evaluations with opposite designs reaching the same verdict is a stronger signal than
either alone.

The manuscript suits this journal because its readership works on the diseases and the
surveillance system the study analyses, and because the Revista has recently published a
review of dengue forecasting and early warning systems covering InfoDengue. A benchmark
that reports where these models fail, and not only where they rank, speaks directly to
readers who would have to act on the forecasts.

The study used exclusively publicly available aggregate surveillance data with no
individual-level records, so ethics committee review was not required. All analysis code,
processed data and the scripts that regenerate every table and figure are openly available
at https://github.com/fabianofilho/dengue-time-series, and reporting follows TRIPOD+AI.

The manuscript is original, has not been published elsewhere, and is not under
consideration by any other journal. All authors have read and approved the submitted
version and agree to transfer the rights of first publication to the Revista da Sociedade
Brasileira de Medicina Tropical upon acceptance. The authors declare no conflicts of
interest and received no external funding. Use of generative AI in preparing the
manuscript is disclosed in the dedicated declaration section.

Yours sincerely,

Fabiano Barcellos-Filho
On behalf of the authors: Fabiano Barcellos-Filho, José Trajano, Wilson Falco
fabiano.nb@gmail.com
