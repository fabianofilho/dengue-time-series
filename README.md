# Previsão de dengue em oito capitais brasileiras

Benchmark de modelos de forecasting para casos mensais de dengue, com dados do
**[InfoDengue](https://info.dengue.mat.br/)** (Fiocruz/FGV) e backtesting por rolling
origin. Compara um foundation model zero-shot (TimesFM 2.5) com modelos treinados para a
tarefa, e mede os dois contra um piso: o naive sazonal.

Os números deste README são gerados por `scripts/build_readme.py` a partir de
`paper/verified_numbers.json` e `results/criterion_summary.json`. Não edite as tabelas à
mão; rode o script.

## Resultado principal

**Nenhum dos sete modelos do artigo bate o naive sazonal pelo critério pré-declarado, em
nenhuma das oito cidades.** O ponto estimado favorece os modelos, e em várias cidades o
intervalo de confiança da diferença exclui zero, mas o teste de Diebold-Mariano por
horizonte não sustenta isso. Os detalhes estão na seção "Comparação contra o piso".

Isto não contradiz que o TimesFM lidere entre os sete modelos comparados. Contradiz a
leitura de que liderar entre eles seja suficiente para recomendar qualquer um deles.

## Coorte e desenho

<!-- BEGIN COORTE (gerado por scripts/build_readme.py, nao editar a mao) -->
- **Período**: fevereiro/2010 a novembro/2024 (178 meses por cidade)
- **Cidades**: 8
- **Modelos**: 7 do artigo, mais o naive sazonal como piso
- **Backtesting**: rolling origin com janela expansiva, horizonte 12 meses, treino mínimo 48 meses, passo 1 mês
- **Folds por cidade**: 119
- **Previsões por modelo por cidade**: 1.428
- **Previsões no total** (7 modelos x 8 cidades): 79.968
- **Métricas**: MAE, RMSE e sMAPE
<!-- END COORTE -->

- **Fonte**: [InfoDengue](https://info.dengue.mat.br/), via API pública
- **Cidades**: São Paulo (SP), Rio de Janeiro (RJ), Belo Horizonte (MG), Brasília (DF),
  Fortaleza (CE), Recife (PE), Manaus (AM), Salvador (BA)
- **Agregação**: os dados chegam por semana epidemiológica. Cada semana é distribuída
  uniformemente pelos seus 7 dias e depois somada por mês do calendário; meses cobertos só
  em parte são descartados. É por isso que a série começa em fevereiro e termina em
  novembro, e não em janeiro e dezembro.

## Modelos

| Modelo | Configuração |
|---|---|
| TimesFM 2.5 | foundation model zero-shot, `google/timesfm-2.5-200m-pytorch`, sem ajuste |
| CatBoost | ForecasterRecursive, 24 lags, verbose=0 |
| XGBoost | ForecasterRecursive, 24 lags, objective=reg:squarederror |
| Random Forest | ForecasterRecursive, 24 lags, n_estimators=100 |
| SARIMAX | order=(1,1,1), seasonal_order=(1,1,0,12) |
| Ridge | ForecasterRecursive, 24 lags, StandardScaler nos lags |
| LightGBM | ForecasterRecursive, 24 lags, random_state=42 |
| Naive sazonal | repete o mesmo mês do ano anterior. É o piso, não um competidor. |
| `global_*` | um modelo nas 8 cidades juntas (ForecasterRecursiveMultiSeries), 24 lags, padronização por série, cidade como indicadora |

O Prophet foi especificado e falhou em 7 das 8 cidades. Não entra em nenhum número
publicado, saiu do default de `--models` e vive em `requirements-optional.txt`.

### Acurácia entre os sete modelos

<!-- BEGIN MODELOS (gerado por scripts/build_readme.py, nao editar a mao) -->
| Modelo | sMAPE médio | sMAPE mediano | Cidades em que lidera (sMAPE) |
|---|---:|---:|---:|
| TimesFM | 74.56 | 70.98 | 7/8 |
| CatBoost | 84.99 | 79.09 | 0/8 |
| XGBoost | 86.67 | 85.13 | 1/8 |
| Random Forest | 88.87 | 83.45 | 0/8 |
| Ridge | 104.27 | 107.06 | 0/8 |
| SARIMAX | 111.18 | 104.26 | 0/8 |
| LightGBM | 113.69 | 108.34 | 0/8 |
<!-- END MODELOS -->

## Comparação contra o piso

<!-- BEGIN BASELINE (gerado por scripts/build_readme.py, nao editar a mao) -->
Critério pré-declarado em [`results/criterion.json`](results/criterion.json), gravado e commitado antes da primeira execução do teste. Um par conta como confirmado quando o IC95% da diferença pareada por bootstrap exclui zero **e** o teste de Diebold-Mariano com correção de Harvey tem p < 0.05 em pelo menos 6 dos 12 horizontes. Bootstrap pareado de janelas inteiras, B = 10.000, semente 20260817.

RelMAE é o MAE do modelo dividido pelo MAE do naive sazonal da mesma cidade. Abaixo de 1 significa que o modelo erra menos que o piso. Não é o MASE do livro, cujo denominador é o erro do naive dentro da amostra de treino.

| Cidade | Melhor modelo (RelMAE) | RelMAE | Melhor por sMAPE | Métricas concordam | Pares confirmados | Bate o piso |
|---|---|---:|---|:-:|---:|---|
| São Paulo | TimesFM | 0.961 | TimesFM | sim | 14/78 | nenhum |
| Rio de Janeiro | TimesFM | 0.851 | TimesFM | sim | 29/78 | nenhum |
| Belo Horizonte | TimesFM | 0.760 | Random Forest global | não | 21/78 | nenhum |
| Brasília | CatBoost | 0.883 | CatBoost global | não | 7/78 | nenhum |
| Fortaleza | TimesFM | 0.841 | TimesFM | sim | 34/78 | nenhum |
| Recife | TimesFM | 0.665 | TimesFM | sim | 19/78 | nenhum |
| Manaus | Random Forest global | 0.830 | Random Forest global | sim | 25/78 | nenhum |
| Salvador | TimesFM | 0.699 | TimesFM | sim | 3/78 | nenhum |

**Resposta: nenhum dos 12 modelos bate o naive sazonal por este critério, em 0 de 8 cidades.** O ponto estimado favorece o melhor modelo em todas as cidades, mas o teste de Diebold-Mariano não acompanha: ele fica bem abaixo dos 6 horizontes exigidos. A análise de sensibilidade em sMAPE, rotulada como exploratória, dá o mesmo veredito nas 8 cidades, mas troca o modelo vencedor em 2 delas.
<!-- END BASELINE -->

## Agrupar as cidades ajuda?

O benchmark treina um modelo por cidade, o que presume que não há nada a aprender de uma
cidade que sirva para outra. Os cinco modelos `global_*` testam essa premissa: um único
modelo treinado nas 8 séries ao mesmo tempo, com padronização por série e a identidade da
cidade como indicadora.

<!-- BEGIN LOCALGLOBAL (gerado por scripts/build_readme.py, nao editar a mao) -->
Diferença de RelMAE, modelo global menos modelo local do mesmo estimador. Negativo significa que agrupar as 8 cidades num modelo só ajudou. O asterisco marca os pares confirmados pelo mesmo critério pré-declarado; sem asterisco o sinal é ponto estimado e não passa no teste.

Comparar global de um estimador com local de outro misturaria o efeito de agrupar com o de trocar de estimador, então a tabela é sempre o mesmo estimador nas duas formas.

| Cidade | CatBoost | LightGBM | Random Forest | Ridge | XGBoost |
|---|---:|---:|---:|---:|---:|
| São Paulo | +0.027 | -0.034 | -0.049 | -0.246 | -0.095 |
| Rio de Janeiro | +0.390 | +0.464 | -1.515 | -0.262 | -1.941 |
| Belo Horizonte | -0.022 | -0.878\* | -0.267 | -0.056 | -0.248 |
| Brasília | +0.024 | -0.116 | -0.062 | -0.053 | -0.070 |
| Fortaleza | -0.142 | -0.621 | -0.972\* | -0.219\* | -0.851\* |
| Recife | -0.237 | -0.485\* | +0.198 | -0.157 | +0.253 |
| Manaus | -0.052 | +0.810 | -0.246\* | +0.757\* | -0.093 |
| Salvador | +0.045 | +0.043 | +0.080 | -0.087 | +0.009 |

**Agrupar ajudou de forma confirmada em 6 de 40 pares cidade-estimador, e atrapalhou em 1.** Nos outros 33 o teste não distingue as duas formas. Nenhum modelo global bate o naive sazonal, e em várias cidades eles ficam bem acima dele: no Rio o melhor global tem RelMAE 1.79, ou seja, erra bem mais que repetir o ano anterior.
<!-- END LOCALGLOBAL -->

## Como usar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

As versões de `lightgbm`, `xgboost` e `catboost` são fixas, não mínimas: as três mudam de
resultado entre versões. Prophet e TimesFM estão em `requirements-optional.txt`.

### 2. Baixar e processar os dados

```bash
python scripts/fetch_infodengue.py --output-dir data/raw
python scripts/process_data.py --input-dir data/raw --output-dir data/processed
```

### 3. Executar o benchmark

```bash
make benchmark-all
```

O alvo termina com código diferente de zero se algum modelo perder alguma janela, dizendo
qual modelo perdeu quais. Sem o TimesFM instalado ele falha, e isso é o comportamento
correto: o resultado publicado inclui o TimesFM.

### 4. Reconstruir as colunas de pareamento em CSVs antigos

```bash
PYTHONPATH=src python scripts/backfill_windows.py --dry-run
```

### 5. Rodar os modelos globais

```bash
PYTHONPATH=src python scripts/run_global_benchmark.py
```

Uma janela produz previsão para as 8 cidades de uma vez, e um erro em qualquer uma
descarta a janela inteira para todas: a janela é a unidade de ajuste, e guardar meia
janela deixaria cidades diferentes com conjuntos de janelas diferentes, quebrando o
pareamento do bootstrap sem avisar.

### 6. Rodar o teste contra o piso

```bash
PYTHONPATH=src python scripts/run_uncertainty.py
```

Lê o critério de `results/criterion.json` e recusa rodar sem ele. Não há opção de linha de
comando para sobrescrever o critério, de propósito.

### 7. Gerar as tabelas, figuras e este README

```bash
PYTHONPATH=src python scripts/build_paper_assets.py
python scripts/build_readme.py
```

## Estrutura do repositório

```
.
├── Makefile
├── requirements.txt                       # os 7 modelos do artigo
├── requirements-optional.txt              # Prophet e TimesFM
├── data/
│   ├── raw/                               # dados brutos da API InfoDengue
│   └── processed/                         # séries mensais processadas
├── paper/                                 # manuscrito, tabelas e figuras geradas
│   └── verified_numbers.json              # todo número citado no texto
├── results/
│   ├── criterion.json                     # critério pré-declarado
│   ├── criterion_summary.json             # veredito contra o piso
│   ├── criterion_verdict_<cidade>.json    # detalhe por cidade
│   ├── uncertainty_<cidade>_*.csv         # bootstrap e testes pareados
│   └── comparisons/
├── scripts/
│   ├── fetch_infodengue.py
│   ├── process_data.py
│   ├── run_benchmark.py                   # backtesting por cidade
│   ├── run_global_benchmark.py            # backtesting multi-serie
│   ├── backfill_windows.py                # window/horizon em CSVs antigos
│   ├── run_uncertainty.py                 # bootstrap, Diebold-Mariano, veredito
│   ├── build_paper_assets.py              # tabelas, figuras, verified_numbers
│   └── build_readme.py                    # os blocos numéricos deste arquivo
├── src/
│   └── dengue_forecast/
│       ├── evaluate.py                    # métricas e backtesting
│       ├── models.py                      # wrappers dos modelos
│       ├── global_models.py               # modelo unico, varias series
│       ├── uncertainty.py                 # bootstrap de janelas e DM
│       ├── intervals.py                   # predição conformal
│       └── ensembles.py
└── tests/
```

## Armadilhas conhecidas

Estão documentadas em `CLAUDE.md`: o scaling do Ridge, a tabela de população do IBGE e a
agregação de semana epidemiológica para mês.

## Próximos passos

1. Variáveis exógenas (temperatura, umidade, pluviometria) via API Mosqlimate, que é a
   lacuna que resta agora que o baseline global foi medido
2. Otimizar hiperparâmetros com `optuna`, medindo o custo do ajuste contra o piso

## Referências

- **InfoDengue**: Sistema de Alerta de Arboviroses, Fiocruz/FGV,
  [info.dengue.mat.br](https://info.dengue.mat.br/)
- **skforecast**: [skforecast.org](https://skforecast.org/)
- Codeço, C.T. et al. (2018). Estimating the effective reproduction number of dengue.
  *Epidemics*, 25, 101–111.
- Bastos, L.S. et al. (2019). A modelling approach for correcting reporting delays in
  disease surveillance data. *Statistics in Medicine*, 38(22), 4363–4377.
- Diebold, F.X. and Mariano, R.S. (1995). Comparing predictive accuracy.
  *Journal of Business and Economic Statistics*, 13(3), 253–263.
- Harvey, D., Leybourne, S. and Newbold, P. (1997). Testing the equality of prediction mean
  squared errors. *International Journal of Forecasting*, 13(2), 281–291.
