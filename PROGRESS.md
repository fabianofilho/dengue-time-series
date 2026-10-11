# PROGRESS: Dengue Forecast Prediction (DFP)

Atualizado em 2026-10-09: pacote de submissão PLOS montado a partir de uma fonte única (ver "Decisões de 09/10").

## Objetivo
Artigo comparando o TimesFM 2.5 zero-shot com modelos treinados por cidade na previsão mensal de dengue em 8 capitais, horizonte de 12 meses, para a **PLOS Neglected Tropical Diseases**.

## Decisões de 04/10/2026 e por quê
- **Este repositório é o canônico.** O `fabianofilho/dengue-timeseries-skforecast` (benchmark v2 e LaTeX PLOS, tag `paper-v2`) fica arquivado. Os dois repositórios eram rascunhos do mesmo estudo com conclusões diferentes, e submeter os dois seria publicação duplicada. Da v2 vieram duas correções, portadas para cá.
- **Revista-alvo: PLOS NTD** (antes era RSBMT; a versão RSBMT fica como histórico).
- **Autores, nesta ordem:** Fabiano Novaes Barcellos Filho (LABDAPS/FSP/USP, correspondente, fabiano.filho@usp.br, ORCID 0000-0002-1491-2700), José Trajano, Wilson Falco e Alexandre Chiavegatto Filho (LABDAPS/FSP/USP, orientador). **Sem financiamento.** As afiliações de José e Wilson eles mesmos preenchem no .docx; nunca inventar.
- **Variantes log1p como emenda EXPLORATÓRIA** em `results/criterion.json`: foi decidida depois de ver resultados (os da v2), então não substitui o veredito confirmatório e o texto tem que dizer isso.
- **IC do sMAPE por janela inteira** (mesmo sorteio do critério, B = 10.000), no lugar do bootstrap iid das 1.428 previsões, que saía estreito demais.

## Decisões de 09/10/2026 e por quê
- **Uma fonte só para o manuscrito:** `paper/plos/manuscript_src.tex`. O texto vivia em dois lugares que divergiram: `paper/manuscript.tex` (parado em 23/09, com as 37 citações e os ICs antigos) e `scripts/build_docx.py` (o que os coautores revisaram, sem citação fora da Introdução e sem a regra de decisão no Methods). `scripts/build_plos.py` gera da mesma fonte o PDF de submissão (`build/plos/manuscript.pdf`, sem figuras, como a PLOS pede), os TIFF (`build/plos/figures/Fig1-10.tif`) e o .docx de revisão (`build/plos/manuscript_review.docx`, via pandoc, com figuras, citações e numeração resolvidas pelo .aux do PDF). Números entram por `\V{expr}` avaliado contra o `verified_numbers.json`; nada digitado.
- **Literatura restaurada e atualizada** (Sprint, Silva, Freitas, Palmer, Bannoud, Belo Horizonte), por decisão do Fabiano: o Wilson revisa e complementa em vez de escrever do zero.
- **Setor do José incluído** (London Institute for Healthcare Engineering, King's College London).
- **Repositório: GitHub público + Zenodo com DOI** (decisão do Fabiano). Abrir o repositório e gerar o DOI ficam para o OK final dele; até lá, `\pending` no texto e no `submission_fields.md`.
- **Aposentados (recuperáveis pelo git):** `paper/manuscript.tex`, `manuscript_rsbmt.tex`, `manuscript.md`, `supplementary.tex`, `submission/cover_letter_rsbmt.md`, `highlights.md`, `peer_review_checklist.md`, `scripts/build_docx.py`, `scripts/check_limits.py`. Sem S1 Appendix: a PLOS não limita tamanho e as 10 tabelas e 10 figuras estão no texto.
- **Correção encontrada no .docx de 06/10:** dizia que o TimesFM é o melhor por MAE em todas as cidades; em Brasília o melhor por MAE é o CatBoost (7 de 8). Agora o número é calculado e o `check_numbers.py` confere.
- **Mudanças de conteúdo em relação ao .docx de 06/10** (listadas no topo do .docx de revisão para os coautores): abstract no formato PLOS e liderado pelo veredito contra o baseline (~300 palavras, o limite); Author summary novo (192 palavras); Methods com regra de decisão, modelos globais e combinações; baseline logo depois do ranking nos Results; literatura restaurada; citações em todo o texto; título passa a nomear o baseline; funding/competing interests/CRediT foram para `paper/plos/submission_fields.md`.
- **Checagens:** `check_numbers.py` (fonte nova, 15 afirmações, os 56 ICs da Tabela 2, carta, literais proibidos como "Barcellos-Filho" e "Google DeepMind"), `check_artifacts.py` (PDF contra .docx), `check_credit.py` (lê `submission_fields.md`). `make paper` roda tudo. Teste de mutação feito: IC alterado e vitória por MAE alterada são acusados.

## Estado
- Confirmatório (critério de 23/09, RelMAE, inalterado): nenhum modelo bate o seasonal naive, 0 de 8 cidades. A sensibilidade em sMAPE concorda.
- Exploratório (log1p): também 0 de 8. RelMAE médio: TimesFM 0,829; CatBoost log 0,872 (1,134 na escala bruta). TimesFM tem o menor valor pontual em 5 de 8, mas contra as variantes log só 3 de 48 pares são confirmados (todos em Brasília), 0 contra o CatBoost log. Leitura: TimesFM comparável aos melhores treinados, não superior.
- `run_uncertainty.py` com escopo explícito: confirmatório e exploratório (`*_exploratorio_log*`) em arquivos separados; o confirmatório reproduz o commitado (ruído < 1e-11 entre Mac e Windows).
- [até 06/10] `build_docx.py` (aposentado em 09/10) gerava o .docx de revisão com a autoria nova, `[PENDING]` nas afiliações de José e Wilson, Métodos e Resultados exploratórios (Tabela 10) e "comparable, not better". Cópias no Drive (`Labs/Dengue Time Series/`, como .docx): versão de 04/10 sem afiliações (id 1BXD-CfJP197kYml5GUrl74OrJRmElaOY, a que foi ao grupo) e versão de 05/10 com afiliações (id 12__dIaNJFzDEYkj1S4z7ls4TyiMHQaDy, linkada na Documentação do projeto). Versão nova não sobrescreve a anterior. A versão de 05/10 foi enviada ao grupo em 05/10 às 21:37, pedindo ao José que confirme a afiliação.
- Documentação do projeto no Drive (Google Doc 1iJsELmCIHUxL5WLn2fRol_Lhf45yq1xtoCmrKRYbQbQ) atualizada em 06/10: link para a versão de 06/10, item de Estado com a intro do Wilson e a confirmação do José, pendência de afiliação removida.
- Versão de 06/10 do .docx (com a Introduction do Wilson; md5 cc9490d3a6ac8c3a3faed910e64f51c6) no Drive (id 11SoDdZ11lw238Op1U2OPyRJLfLuul7yv) e enviada ao grupo em 06/10 às 06:41 pelo Fermes (status ok em ver_envios), com aviso de que o número da OMS está PENDING e de que a ref. 5 (TimesFM-3) ficou de fora.
- LAB-135 (05/10): comentário registrando que o critério de 23/09 (commit 0f7fdd6, fixado 4 min antes da primeira rodada) resolve o bloqueio para a publicação de dengue. A issue já estava Done pelo lado do OPT.
- 05/10 07:10: mensagem com as decisões, o deck (`scripts/build_deck.py` gera `build/DFP_deck_pipeline_AAAA-MM-DD.pdf`, 11 slides, números do verified_numbers) e o .docx de revisão enviados ao grupo de WhatsApp "Artigo pred dengue" (José e Wilson) pelo Fermes. O Alexandre não está no grupo; o Fabiano fala com ele. O grupo tem 3 participantes, mas a busca só identificou o Wilson pelo nome: confirmar que o José recebeu. Os arquivos enviados ficaram em `/opt/fermes-mcp/uploads` na VPS.
- Remoto em dia em 07/10. Próxima sessão: `git fetch` antes de tudo e `/zap grupo` para ler o que chegou no grupo desde 07/10.

## Retorno do grupo (05/10, lido na Evolution API)
Só o Wilson escreveu; o José não se manifestou no grupo (o Wilson mandou a afiliação dele).
- **Afiliações (enviadas pelo Wilson às 19:41):**
  - Wilson Falco: Faculdade de Medicina de Catanduva, São Paulo, Brazil.
  - José Trajano Feitosa Filho (nome completo): King's College London, London, United Kingdom. **Confirmado pelo José em 06/10 00:00.** Setor London Institute for Healthcare Engineering incluído em 09/10 (decisão do Fabiano). Contatos dos coautores ficam na memória do projeto, não aqui.
- **Enquadramento:** o Wilson achou o reframe "bom, mais robusto" e a Discussion boa.
- **Tipo de artigo:** o Wilson perguntou o formato (está olhando as guidelines da PLOS NTD). O Fabiano respondeu que a Introduction deve ser curta, um parágrafo só.
- **Introdução:** o Wilson redigiu um parágrafo novo (18:36), com referências [1], [2], [3] e [5]. Antes de usar: conferir na fonte o número "5,421,759 cases and 4,066 deaths worldwide in 2025 [1]" (abrangência e ano), achar a referência [4] que falta na numeração, e alinhar a última frase com o texto atual ("six purpose-trained models" bate com os 7 modelos: 6 treinados + TimesFM).
- **Discussion:** o Wilson se ofereceu para acrescentar referências de benchmarking e comparação com outros estudos brasileiros. O Fabiano autorizou ("pode mexer sim").
- **06/10 00:11:** o Wilson mandou `DFP_introducao_referencias_2026-10-05.docx` (baixado pela Evolution para `build/coautores/`, fora do git): a Introduction de um parágrafo, agora com citações [1] a [4], e 5 referências. Ele também achou bom o parágrafo da escala log e sugeriu referenciar mais os métodos e talvez acrescentar um parágrafo.
- **Incorporado em 06/10 no `build_docx.py`:** seção INTRODUCTION entre Abstract e Methods, com o texto do Wilson (contagens de modelos e cidades e o período vêm do verified_numbers; o período ficou "February 2010 to November 2024") e seção REFERENCES com as 4 citadas em Vancouver. A ref. 4 (Das) segue a versão publicada (ICML 2024), não o preprint. A entrada `WHO2025dengue` foi para o `references.bib`.
- **Não incorporado:** a ref. 5 do Wilson (Jain e Sen, blog do TimesFM-3, Google Research, 31/08/2026; a página existe) não é citada no texto. Caberia na limitação de checkpoint único ou junto de "sem covariáveis", já que o TimesFM-3 aceita covariáveis. Decidir com o Wilson.
- **A conferir:** o número da OMS (5.421.759 casos e 4.066 óbitos em 2025) foi lido pelo Wilson no painel da OMS em 05/10/2026. O painel é ao vivo e não foi reproduzido aqui; um informe da OMS fala em mais de 5 milhões de casos e mais de 3.000 óbitos até o início de dezembro de 2025, o que é coerente. Ficou `[PENDING]` no .docx.

- **06/10 depois do envio da versão de 06/10 (lido em 07/10):** o Wilson reagiu e disse que "mais tarde" vê o ponto do número da OMS e da ref. 5. Sobre o repositório: "pessoalmente tanto faz", e lembrou que o GitHub rende visualizações; a decisão fica com o Fabiano (sugestão: GitHub público com arquivamento no Zenodo pela integração, para citar DOI). Duas mensagens dele às 12:34 e 12:41 não são legíveis pela Evolution (provavelmente visualização única ou enquete): conferir no celular. O José não se manifestou depois da confirmação da afiliação.

Comunicação: grupo de WhatsApp "Artigo pred dengue" (conectado na /zap em 07/10).

- **11/10 19:33:** versão de 11/10 do .docx de revisão (gerada pelo `build_plos.py` no commit a742390; md5 45e741c8a8e7fbdfacebafe1c4ce1683) no Drive (`Labs/Dengue Time Series/DFP_manuscrito_revisao_coautores_2026-10-11.docx`, id 1djcKq3DzdGR6lpdAg-XyDLcNLrkwxeuT) e enviada ao grupo pelo Fermes (status ok), com a lista do que mudou, o pedido ao Wilson (literatura e número da OMS), a correção do MAE, a afiliação do José, a decisão GitHub + Zenodo e os papéis do CRediT no texto para cada um conferir. A Documentação do projeto no Drive foi atualizada em 11/10 (link da versão de 11/10, setor do José, item de Estado sobre o template PLOS e pendências refeitas).

## Próximos passos
1. **Coautores:** [enviado ao grupo em 11/10] esperar o retorno do José e do Wilson (literatura, número da OMS, CRediT); o Fabiano manda ao Alexandre. Ler o grupo: `/zap grupo`.
2. **Número da OMS** (`\pending` na Introdução): o Wilson confere no painel; se não voltar, trocar pelo informe da OMS (mais de 5 milhões de casos e mais de 3.000 óbitos em 2025).
3. **Repositório público + Zenodo:** antes de abrir, limpar o que ainda for pessoal (o histórico tem e-mails dos coautores no PROGRESS desde o commit 2ac64d6; recomendação: manter o histórico, porque ele prova a ordem dos commits do critério; confirmar com o Fabiano). Depois, release no GitHub com a integração do Zenodo, DOI no Methods (`\pending`) e no `submission_fields.md`.
4. **CRediT:** confirmar os papéis com José, Wilson e Alexandre (Alexandre hoje só com Supervision e revisão).
5. **Submissão:** taxa e Fee Assistance conferidos no navegador (as páginas recusaram acesso automatizado; US$ 2.670 é dado indireto); ORCID do autor correspondente no sistema; subir PDF, TIFF e carta conforme `paper/plos/submission_fields.md`.
6. Opcional: a ref. 5 do Wilson (blog do TimesFM-3) e a `McGough2021` (no .bib, não citada).
7. Opcional: checklist TRIPOD+AI como S1 (a PLOS não exige para este tipo de estudo).

Para reenviar material ao grupo: `make paper PYTHON=.venv/bin/python` (ou `python scripts/build_plos.py`) e `build_deck.py`; copiar por scp (root) para `/opt/fermes-mcp/uploads` com dono `automacoes`, e mandar pelo Fermes só depois do OK do Fabiano.

## Restrições
- Números só por script (`paper/verified_numbers.json`, `build_paper_assets.py`); nada digitado.
- Commit local por etapa; **push só com OK do Fabiano**.
- Ambiente: `.venv` com Python 3.12, os pins de `requirements.txt` e, para o TimesFM, `torch==2.8.0` + timesfm no commit `8a755c9` (`requirements-optional.txt`). Com torch 2.14 e timesfm 3.x o LightGBM dá segfault no macOS ARM.
- Toda contagem "por cidade" depende de quais modelos estão no CSV: o conjunto confirmatório é o de `criterion.json`, nunca o CSV inteiro.

## Descartado
- Afirmar superioridade do TimesFM ("7 de 8"): depende do conjunto comparado e não sobrevive aos modelos treinados em log.
- Submeter o manuscrito do repo `dengue-timeseries-skforecast`.
- RSBMT como revista-alvo.
