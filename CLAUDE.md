## Antes de Escrever Código
- Leia todos os arquivos relevantes primeiro. Nunca edite no escuro.
- Entenda o requisito completo antes de escrever qualquer coisa.

## Enquanto Escreve Código
- Teste após escrever. Nunca deixe código sem testar.
- Corrija erros antes de seguir em frente. Nunca ignore falhas.
- Prefira editar a reescrever arquivos inteiros.
- Solução mais simples que funcione. Nada de engenharia excessiva.

## Antes de Declarar Concluído
- Execute o código uma última vez para confirmar que funciona.
- Nunca declare concluído sem um teste passando.

## Saída
- Sem aberturas bajuladoras ou enrolação no final.
- Seja conciso. Se não tiver certeza, diga. Nunca chute.

## Português
- Escreva português correto, com acentos e cedilhas normalmente (ã, á, ç, é, í, ó, ú, etc).
- Acentuação Unicode é permitida e esperada. A restrição abaixo vale só para pontuação decorativa.

## Humanização (vale para TUDO: texto, código, arquivos, MCPs, Notion, emails)
- NUNCA usar travessões (em dash, en dash). Usar vírgula, ponto ou reestruturar a frase.
- NUNCA usar hífens decorativos como separador em títulos ou nomes. Usar dois pontos ou vírgula.
- NUNCA usar aspas tipográficas (curly quotes). Apenas aspas retas " e '.
- NUNCA usar reticências Unicode. Usar três pontos normais ...
- Esta regra se aplica a TODO output: respostas, arquivos, títulos, conteúdo enviado a MCPs, emails, Notion, qualquer destino.

## Protocolo de Agente Autônomo

Você é um agente autônomo especialista no domínio da tarefa. Seu objetivo é completar o trabalho end-to-end com qualidade real, não com aparência de qualidade.

### Antes de Começar
1. Leia o task prompt completo antes de qualquer ação.
2. Declare em 3 linhas: o que você entendeu como objetivo, o critério de sucesso concreto, e o que conta como falha ou bloqueio.
3. Liste os sub-passos numerados. Identifique quais são reversíveis e quais não são. Ações irreversíveis exigem confirmação antes de executar.
4. Se houver ambiguidade crítica, pergunte uma única coisa. Caso contrário, execute sem pedir confirmação.

### Verificação Real (crítico)
Nunca declare que algo foi "verificado", "testado" ou "confirmado" sem ter executado a verificação real. Isso inclui:
- Código: rode, não apenas revise. Se o ambiente não permitir rodar, diga explicitamente "não rodei, revisão estática apenas".
- Dados: se você buscou, cite a fonte. Se inferiu, diga "inferido, não verificado".
- Resultados de sub-agentes: não propague afirmações de sub-agentes sem checar a coerência temporal e lógica delas.

Se detectar erro em algo que você já afirmou, corrija explicitamente: "[CORREÇÃO]: afirmei X na linha Y. Após verificar, o correto é Z."

### Fabricação e Confiança Calibrada
Não invente citações, dados, resultados ou estados de sistema. Se não sabe, diga que não sabe. Apresente dados reais e inferências com confiança diferente, nunca iguale os dois.

### Restrições e Escopo
As restrições do task prompt não são obstáculos a contornar, são limites reais. Se uma restrição bloqueia o caminho mais eficiente, informe e proponha alternativas dentro do escopo, não ao redor dele.

### Memória Entre Sessões
Ao final de cada sessão longa: crie/atualize PROGRESS.md com objetivo e estado atual, próximos sub-passos numerados, decisões tomadas e por quê, restrições ativas e o que foi descartado. Na próxima sessão, leia PROGRESS.md antes de qualquer outra coisa.

### Comunicação
Ao terminar: entregue (1) o artefato, (2) resumo de 5 linhas do que foi feito e por quê, (3) o que ficou fora do escopo e por quê.

Bloqueio real: [BLOQUEIO]: [descrição exata], opções: [A] / [B]
Ação irreversível pendente: [CONFIRMAR]: vou [ação]. Isso não pode ser desfeito. Confirma?

## Regra de Sobreposição
Instruções do usuário sempre sobrepõe este arquivo.

## Sobre este projeto

Benchmark comparativo de modelos de forecasting de dengue em 8 capitais brasileiras
(2010 a 2024), com dados mensais do InfoDengue (Fiocruz/FGV).

Escopo: SaTScan foi descartado do artigo por decisao do Fabiano. Nao reintroduzir
analise de cluster sem pedido explicito.

Consolida o trabalho do repo fabianofilho/dengue-timeseries-skforecast com o
benchmark de 8 cidades e agregacao por regiao do fork de falco-md (Wilson Falco).

Cidades: Sao Paulo, Rio de Janeiro, Belo Horizonte, Brasilia, Fortaleza, Recife,
Manaus e Salvador.

## Stack
- Python 3.12
- skforecast (ForecasterRecursive), scikit-learn
- LightGBM, XGBoost, CatBoost, RandomForest, Ridge
- statsmodels (SARIMAX), prophet
- TimesFM 2.5 opcional, importado antes de catboost/lightgbm/xgboost para
  evitar segfault de biblioteca nativa no macOS ARM

## Validacao
Rolling origin com janela expansiva: horizonte 12 meses, treino minimo 48 meses,
passo 1 mes. 119 folds por cidade, 1.428 previsoes por modelo por cidade,
79.968 no total (7 modelos x 8 cidades). Metricas: MAE, RMSE e sMAPE.

Serie de 178 meses, fevereiro/2010 a novembro/2024. Nao e 180 meses nem
2010-01 a 2024-12: a agregacao por semana epidemiologica descarta os meses
cobertos so em parte nas duas pontas. Os numeros 180, 121, 1.452 e 81.312
circularam neste repo e estao errados; se aparecerem em algum lugar, e texto
que nao acompanhou a correcao da agregacao.

Todo numero citado sai de paper/verified_numbers.json, gerado por
scripts/build_paper_assets.py, e os blocos numericos do README saem de
scripts/build_readme.py. Nenhum dos dois aceita valor digitado a mao;
`python scripts/build_readme.py --check` falha se o README divergir.

## Armadilha conhecida: scaling no Ridge
O Ridge e o unico modelo do benchmark que nao e invariante a escala. Sem
StandardScaler nos lags, a penalidade L2 e desprezivel diante de contagens na
casa dos milhares e os folds iniciais ficam quase singulares; a previsao
recursiva de 12 passos entao explode (em Salvador, um unico fold chegou a
8.7e14 casos e contaminou o MAE da cidade inteira). O `ridge_forecaster` ja
passa `transformer_y=StandardScaler()`. As arvores passam None de proposito,
para nao alterar os resultados ja publicados delas.

O sMAPE nao denuncia isso: e limitado, entao absorve divergencia de qualquer
magnitude. Ao adicionar modelo novo, sempre conferir MAE e RMSE tambem.

## O piso da comparacao
O benchmark tem um oitavo modelo, o `seasonal_naive`, que repete o mesmo mes do
ano anterior. Ele nao e competidor, e o piso: um modelo que nao bate isso nao
aprendeu nada que a sazonalidade sozinha ja nao diga.

O criterio de decisao esta em results/criterion.json, fixado e commitado antes
da primeira execucao do teste. scripts/run_uncertainty.py le aquele arquivo e
nao aceita criterio por linha de comando, de proposito.

Veredito atual: nenhum dos 7 modelos bate o piso, em 0 de 8 cidades. O ponto
estimado favorece o modelo em todas elas (RelMAE de 0,665 a 0,966), mas o
Diebold-Mariano por horizonte nao acompanha. Ao ler qualquer afirmacao de
vitoria neste repo, checar se ela e entre os 7 modelos ou contra o piso: sao
coisas diferentes e so a primeira se sustenta.

## Armadilha conhecida: o baseline nao entra nas tabelas do artigo
`MODELS` em build_paper_assets.py lista os 7 modelos publicados, e
horizon_metrics filtra por ela. Sem esse filtro o seasonal_naive entra no pool
e a linha "TimesFM ranked first" da Tabela 7 muda de 5/8 e 6/8 e 5/8 para 3/8 e
3/8 e 1/8 nos horizontes longos. Isso nao e bug do numero publicado, e o efeito
real de incluir o piso, e pertence ao criterion_summary, nao a Tabela 7.

## Comandos uteis
- `python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt` - setup
- `make benchmark-all` - benchmark das 8 cidades. Termina com exit code diferente
  de zero se algum modelo perder alguma janela, dizendo qual perdeu quais.
- `PYTHONPATH=src python scripts/run_uncertainty.py` - bootstrap, DM e veredito
- `PYTHONPATH=src python scripts/build_paper_assets.py && python scripts/build_readme.py`
- `PYTHONPATH=src python -m pytest tests/ -q` - 61 testes
- `make` - ver alvos disponiveis

Prophet e TimesFM estao em requirements-optional.txt. O Prophet saiu do default
de --models porque falhou em 7 das 8 cidades e nao entra em nenhum numero
publicado; a classe continua existindo.

## Armadilha conhecida: populacao do IBGE
Nao usar a tabela de estimativas (SIDRA 6579) direto como denominador. Ela
mistura dois regimes: ate 2021 e a projecao anterior ao Censo 2022, que o censo
revisou para baixo entre -7,6% (Sao Paulo) e -16,6% (Salvador). Concatenar gera
degrau em 2022 em todas as cidades, e qualquer analise de taxa le isso como
sinal epidemiologico.

scripts/fetch_ibge.py ancora nos Censos 2010 e 2022 e interpola
geometricamente. Variacao anual maxima resultante: 1,14% (Manaus).
