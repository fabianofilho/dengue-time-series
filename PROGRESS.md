# PROGRESS: Dengue Forecast Prediction (DFP)

Atualizado em 2026-10-06, sessão encerrada depois de enviar ao grupo a versão de 06/10 do .docx (introdução do Wilson incorporada).

## Objetivo
Artigo comparando o TimesFM 2.5 zero-shot com modelos treinados por cidade na previsão mensal de dengue em 8 capitais, horizonte de 12 meses, para a **PLOS Neglected Tropical Diseases**.

## Decisões de 04/10/2026 e por quê
- **Este repositório é o canônico.** O `fabianofilho/dengue-timeseries-skforecast` (benchmark v2 e LaTeX PLOS, tag `paper-v2`) fica arquivado. Os dois repositórios eram rascunhos do mesmo estudo com conclusões diferentes, e submeter os dois seria publicação duplicada. Da v2 vieram duas correções, portadas para cá.
- **Revista-alvo: PLOS NTD** (antes era RSBMT; a versão RSBMT fica como histórico).
- **Autores, nesta ordem:** Fabiano Novaes Barcellos Filho (LABDAPS/FSP/USP, correspondente, fabiano.filho@usp.br, ORCID 0000-0002-1491-2700), José Trajano, Wilson Falco e Alexandre Chiavegatto Filho (LABDAPS/FSP/USP, orientador). **Sem financiamento.** As afiliações de José e Wilson eles mesmos preenchem no .docx; nunca inventar.
- **Variantes log1p como emenda EXPLORATÓRIA** em `results/criterion.json`: foi decidida depois de ver resultados (os da v2), então não substitui o veredito confirmatório e o texto tem que dizer isso.
- **IC do sMAPE por janela inteira** (mesmo sorteio do critério, B = 10.000), no lugar do bootstrap iid das 1.428 previsões, que saía estreito demais.

## Estado
- Confirmatório (critério de 23/09, RelMAE, inalterado): nenhum modelo bate o seasonal naive, 0 de 8 cidades. A sensibilidade em sMAPE concorda.
- Exploratório (log1p): também 0 de 8. RelMAE médio: TimesFM 0,829; CatBoost log 0,872 (1,134 na escala bruta). TimesFM tem o menor valor pontual em 5 de 8, mas contra as variantes log só 3 de 48 pares são confirmados (todos em Brasília), 0 contra o CatBoost log. Leitura: TimesFM comparável aos melhores treinados, não superior.
- `run_uncertainty.py` com escopo explícito: confirmatório e exploratório (`*_exploratorio_log*`) em arquivos separados; o confirmatório reproduz o commitado (ruído < 1e-11 entre Mac e Windows).
- `build_docx.py` gera o .docx de revisão com a autoria nova, `[PENDING]` nas afiliações de José e Wilson, Métodos e Resultados exploratórios (Tabela 10) e "comparable, not better". Cópias no Drive (`Labs/Dengue Time Series/`, como .docx): versão de 04/10 sem afiliações (id 1BXD-CfJP197kYml5GUrl74OrJRmElaOY, a que foi ao grupo) e versão de 05/10 com afiliações (id 12__dIaNJFzDEYkj1S4z7ls4TyiMHQaDy, linkada na Documentação do projeto). Versão nova não sobrescreve a anterior. A versão de 05/10 foi enviada ao grupo em 05/10 às 21:37, pedindo ao José que confirme a afiliação.
- Documentação do projeto no Drive (Google Doc 1iJsELmCIHUxL5WLn2fRol_Lhf45yq1xtoCmrKRYbQbQ) atualizada em 06/10: link para a versão de 06/10, item de Estado com a intro do Wilson e a confirmação do José, pendência de afiliação removida.
- Versão de 06/10 do .docx (com a Introduction do Wilson; md5 cc9490d3a6ac8c3a3faed910e64f51c6) no Drive (id 11SoDdZ11lw238Op1U2OPyRJLfLuul7yv) e enviada ao grupo em 06/10 às 06:41 pelo Fermes (status ok em ver_envios), com aviso de que o número da OMS está PENDING e de que a ref. 5 (TimesFM-3) ficou de fora.
- LAB-135 (05/10): comentário registrando que o critério de 23/09 (commit 0f7fdd6, fixado 4 min antes da primeira rodada) resolve o bloqueio para a publicação de dengue. A issue já estava Done pelo lado do OPT.
- 05/10 07:10: mensagem com as decisões, o deck (`scripts/build_deck.py` gera `build/DFP_deck_pipeline_AAAA-MM-DD.pdf`, 11 slides, números do verified_numbers) e o .docx de revisão enviados ao grupo de WhatsApp "Artigo pred dengue" (José e Wilson) pelo Fermes. O Alexandre não está no grupo; o Fabiano fala com ele. O grupo tem 3 participantes, mas a busca só identificou o Wilson pelo nome: confirmar que o José recebeu. Os arquivos enviados ficaram em `/opt/fermes-mcp/uploads` na VPS.
- Remoto em dia em 06/10 (push depois do envio da versão de 06/10). Próxima sessão: `git fetch` antes de tudo.

## Retorno do grupo (05/10, lido na Evolution API)
Só o Wilson escreveu; o José não se manifestou no grupo (o Wilson mandou a afiliação dele).
- **Afiliações (enviadas pelo Wilson às 19:41):**
  - Wilson Falco: Faculdade de Medicina de Catanduva, São Paulo, Brazil (wilson.academic.mail@gmail.com).
  - José Trajano Feitosa Filho (nome completo): King's College London, London, United Kingdom. **Confirmado pelo José em 06/10 00:00.** E-mail acadêmico: jose.filho@kcl.ac.uk (o jttrajano@me.com veio do Wilson). Opcional, sugerido pelo José: setor London Institute for Healthcare Engineering.
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

## Próximos passos
1. Esperar do Wilson as referências de métodos e de benchmarking e a comparação com estudos brasileiros na Discussion, e o retorno do Alexandre (o Fabiano fala com o Alexandre). Para ler o grupo de novo: `chat/findMessages` da Evolution com o ambiente do serviço `fermes-mcp` (chave em `/opt/whatsapp-bot/.env`), remoteJid `120363163601111597@g.us`.
2. [feito 05-06/10] Afiliações e nome completo do José no `build_docx.py`, já confirmados pelo José. Decidir se entra o setor do José (London Institute for Healthcare Engineering). Falta levar ao `.tex` de submissão.
3. [intro feita 06/10] Introduction do Wilson no .docx; no `.tex` de submissão, a seção Introduction atual será substituída por ela (citando `WHO2025dengue`, `Leung2023`, `Roster2022`, `Das2024timesfm`). Decidir se a frase final menciona também os 5 modelos globais multi-série. A Discussion do Wilson, quando vier, entra conferindo cada número e referência na fonte.
4. Decidir sobre o repositório privado: abrir ou depositar no Zenodo com DOI. A frase de disponibilidade de código depende disso.
5. Atualizar o manuscrito de submissão no template LaTeX da PLOS NTD (Research Article; template oficial v3.8, `plos2025.bst`; a conversão no repo arquivado em `paper/plos/` serve de modelo). Os `.tex` atuais deste repo ainda trazem os ICs antigos (bootstrap iid), "Barcellos-Filho", "Google DeepMind", autoria sem Alexandre e nada da análise exploratória.
6. Incluir os ICs na lista curada do `scripts/check_numbers.py`: hoje ele não detecta IC defasado no texto.
7. Opcional: renderizar o .docx em PDF para conferência visual (só houve validação estrutural).

Para reenviar material ao grupo: regenerar com `build_docx.py`/`build_deck.py`, copiar por scp (root) para `/opt/fermes-mcp/uploads` com dono `automacoes`, e mandar pelo Fermes só depois do OK do Fabiano.

## Restrições
- Números só por script (`paper/verified_numbers.json`, `build_paper_assets.py`); nada digitado.
- Commit local por etapa; **push só com OK do Fabiano**.
- Ambiente: `.venv` com Python 3.12, os pins de `requirements.txt` e, para o TimesFM, `torch==2.8.0` + timesfm no commit `8a755c9` (`requirements-optional.txt`). Com torch 2.14 e timesfm 3.x o LightGBM dá segfault no macOS ARM.
- Toda contagem "por cidade" depende de quais modelos estão no CSV: o conjunto confirmatório é o de `criterion.json`, nunca o CSV inteiro.

## Descartado
- Afirmar superioridade do TimesFM ("7 de 8"): depende do conjunto comparado e não sobrevive aos modelos treinados em log.
- Submeter o manuscrito do repo `dengue-timeseries-skforecast`.
- RSBMT como revista-alvo.
