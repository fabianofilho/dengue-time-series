# Conferência das afirmações sobre outros estudos (14/10/2026)

Cada afirmação do `manuscript_src.tex` atribuída a um estudo de outro grupo foi conferida na
fonte (Europe PMC e texto completo no PMC quando aberto; senão o abstract). Os trechos vieram
do texto de 23/09 e não tinham sido reconferidos. Conferi à parte, nos abstracts do Europe PMC,
os quatro achados mais graves (Fang2024, Chen2025rj, Barcellos2024, Chen2025lstm).

Legenda: OK = confere; PARCIAL = exagera ou simplifica; NÃO = a fonte não sustenta ou contradiz.

## Não conferem (corrigir antes de submeter)

| Onde | Afirmação no texto | Ref | O que a fonte diz |
|---|---|---|---|
| Comparison with the literature | "tree-based models beat classical parametric ones" é achado consistente | Fang2024 | Revisão de 23 estudos de ML; os melhores mais citados foram SVM e LSTM; não compara árvores com paramétricos. |
| Comparison with the literature | (o mesmo achado) | Chen2025rj | No Rio, sem covariáveis, o ARIMA foi o melhor modelo estatístico e superou RF e XGBoost; contradiz a frase. |
| Comparison with the literature | benchmarks comparam ARIMA contra árvores | Sebastianelli2024 | Ensemble CatBoost+SVM+LSTM, nível estadual, 1 mês; sem ARIMA contra árvores. |
| Comparison with the literature | LSTM "precisa de histórico por cidade e degrada sob mudança de distribuição" | Chen2025lstm | Estudo nos 27 estados, não em cidades; não discute histórico necessário nem mudança de distribuição. |
| Limitations | covariáveis de clima superam abordagens univariadas para início de surto | Barcellos2024 | Estudo explicativo (expansão da dengue, anomalias térmicas), não de previsão; não compara com univariado. |
| Introduction | modelos de fundação não foram avaliados extensamente em dengue brasileira | Lau2026foundation | É um Perspective sobre modelos de fundação em epidemias, sem avaliação empírica; a lacuna é inferência nossa. |

## Parciais (ajustar a redação)

| Onde | Afirmação | Ref | Ajuste |
|---|---|---|---|
| Introduction (Wilson) | "from univariate to multivariate, from seasonal ARIMA to neural networks" | Leung2023 | Abstract fala de 99 modelos de 64 estudos, estatísticos e de ML; "univariado/multivariado" e "ARIMA sazonal" não aparecem no abstract (corpo não lido). |
| Introduction (Wilson) | acurácia "differs substantially" entre cidades | Roster2022 | Sustenta que o melhor modelo muda por cidade; não sustenta "substantially". |
| Comparison with the literature | Sprint "prospective" | Araujo2026sprint | 2024 foi calibração retrospectiva; só 2025 foi previsão real. |
| Comparison with the literature | Bannoud pôs "a gradient boosting method" no topo | Bannoud2026augment | Os melhores foram AdaBoost e CatBoost; horizonte de 1 semana. |
| Comparison with the literature | Palmer: "the best performer was the simplest specification" | Palmer2026hosp | Foram dois modelos (só internação e só clima). |
| Results | 2024 "the largest in Brazilian records" | GurgelGoncalves2024 | Título e texto sustentam, mas com dados até junho de 2024 (projeção). |
| Limitations | notificados sub-representam infecções | Siqueira2022 | A revisão diz que o ônus é provavelmente subestimado; a ligação com notificação é nossa. |

## Conferem

Araujo2026sprint (seis equipes internacionais, cinco estados, nenhum modelo se destacou de forma
consistente, ensembles adotados pelas autoridades), Silva2026capitals (27 capitais, até 4
semanas, covariáveis climáticas e socioeconômicas), Freitas2025bands (118 distritos, 52 semanas,
bandas bayesianas), Palmer2026hosp (8 semanas, 27 regiões imediatas, atraso de até 8 semanas,
buscas de médicos), Bannoud2026augment (14 algoritmos, aumento de dados reduziu o erro acima do
máximo do treino), Leung2023 (relato de métricas inadequado), Chen2025rj (uma cidade só).

## Não conferido

Métodos clássicos (Das2024timesfm, Ansari, Woo, Gibbs, Hewamalage, Kapoor, Tashman, Hyndman,
Breiman, Chen2016, Ke2017, Prokhorenkova): sem afirmação específica checável. WHO2025dengue já
está como pendência. Codeco2018infodengue existe (resumo de congresso na Rev Epidemiol Santé
Publique 2018;66:S386); a frase sobre o SINAN não foi conferida nele.
