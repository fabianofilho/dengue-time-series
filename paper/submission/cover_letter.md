# Cover Letter

> Carta alternativa, para o caso de a submissao a Revista da Sociedade Brasileira de
> Medicina Tropical nao seguir adiante. A carta da revista alvo e
> `cover_letter_rsbmt.md`. A afiliacao continua pendente e esta marcada abaixo.

Dear Editor,

We submit our manuscript "Zero-Shot Foundation Models Versus Purpose-Trained Models for
Dengue Forecasting in Eight Brazilian State Capitals (2010 to 2024): A Rolling-Origin
Benchmark" for consideration as an original research article in PLOS Neglected Tropical
Diseases.

Dengue affects millions of Brazilians each year, with 2024 recording the highest burden on
record. Forecasting monthly case counts matters for planning vector control, procurement
and hospital capacity. Most available tools require city-specific training and frequent
retraining, a maintenance burden that limits scaling across the 5,570 municipalities
covered by Brazil's surveillance network. We evaluated whether a zero-shot foundation model
can substitute for that pipeline, and, once the work was under way, whether any model in
the comparison is worth running at all.

The second question is the one we lead with, and the answer is no. We benchmarked seven
models on 15 years of monthly InfoDengue data for eight capitals under a single
rolling-origin design (119 folds per city, 79,968 predictions), and compared every one of
them against a seasonal naive forecast that repeats the same month of the previous year.
The decision rule was written to the project repository and committed before the comparison
ran, so the ordering is verifiable in the public history. No model beats that baseline in
any of the eight cities: point estimates favour the models, with the best model in each
city reaching a relative MAE between 0.665 and 0.961, but a Diebold-Mariano test rejects
equal accuracy at no more than three of the twelve horizon steps, against the six the rule
requires. In Belo Horizonte the baseline is better than every model we fitted on the
study's primary metric.

Within the model comparison, TimesFM 2.5 ranked first by sMAPE in seven of eight cities
without any city-specific training, averaging 74.6% against 85.0% for CatBoost. That
advantage is about the cost of the pipeline rather than forecast quality, and it depends on
which models are compared: adding five global models fitted on all cities jointly moves the
count to five of eight. The margin is also city-dependent, and in Sao Paulo the two leading
models have overlapping intervals (75.5% against 80.1%), so we do not treat that gap as
established.

We present this as a reference benchmark rather than as support for deployment, and we
recommend that dengue forecasting studies report a trivial baseline and a pre-registered
decision rule as a matter of course. Without both, a ranking among models is compatible
with none of the models being useful.

The manuscript has not been submitted elsewhere. All authors contributed substantially and
approved the final version. We declare no conflict of interest and received no external
funding. Code, processed data, the pre-registered decision rule and the scripts that
regenerate every table and figure are publicly available at
https://github.com/fabianofilho/dengue-time-series. Reporting follows TRIPOD+AI.

Sincerely,

Fabiano Barcellos-Filho
[Institution: to complete]
fabiano.nb@gmail.com
