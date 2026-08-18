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

We report three results that qualify that finding rather than support it, and we consider
them the more useful contribution to your readership. First, the three accuracy metrics
select different models in half the cities, and in two of them each metric names a
different winner, so a single-metric benchmark would have reached a different conclusion.
Second, conformal prediction intervals were close to calibrated across the study period
but coverage fell to 69.2% during the 2024 epidemic, meaning the intervals fail precisely
when a surveillance system would rely on them. Third, combining the models did not beat
the best single model in seven of eight cities. Taken together these argue against
deploying any single model on the strength of a benchmark, and they converge with the
conclusion of the 2024 Dengue Forecasting Sprint, reached prospectively and at state
level with climate covariates, that no model excelled consistently and that 2024 defeated
every approach.

The manuscript suits this journal because its readership works on the diseases and the
surveillance system the study analyses. The Revista has recently published a review of
dengue forecasting and early warning systems covering InfoDengue, and this manuscript
supplies the standardised municipal benchmark that such reviews report as missing.

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
