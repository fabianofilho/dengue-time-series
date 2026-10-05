"""
Gera o deck do pipeline e dos resultados para os coautores (PDF, beamer 16:9).

Todo numero vem de paper/verified_numbers.json; nenhum e digitado aqui. As
figuras sao as PNG de paper/figures, as mesmas do manuscrito.

Uso:
    python scripts/build_deck.py [--out build/DFP_deck_pipeline_AAAA-MM-DD.pdf]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
TECTONIC = "/opt/miniconda3/envs/tectonic/bin/tectonic"

CITY_PT = {
    "Sao Paulo": "São Paulo", "Rio de Janeiro": "Rio de Janeiro", "Belo Horizonte": "Belo Horizonte",
    "Brasilia": "Brasília", "Fortaleza": "Fortaleza", "Recife": "Recife", "Manaus": "Manaus",
    "Salvador": "Salvador",
}
MODEL_PT = {
    "timesfm": "TimesFM", "catboost": "CatBoost", "xgboost": "XGBoost", "randomforest": "Random Forest",
    "sarimax": "SARIMAX", "ridge": "Ridge", "lgbm": "LightGBM", "global_randomforest": "RF global",
    "global_catboost": "CatBoost global",
}


def br(x: float, nd: int = 1) -> str:
    """Numero no formato brasileiro (virgula decimal, ponto de milhar)."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def model_name(m: str) -> str:
    if m.endswith("_log"):
        return MODEL_PT.get(m[:-4], m[:-4]) + " log"
    return MODEL_PT.get(m, m)


def build(v: dict, crit: dict) -> str:
    ms = v["mean_smape_by_model"]
    b = v["baseline"]
    h = v["horizon"]
    ex = v["exploratory_log"]
    g = v["global_models"]
    iv = v["intervals"]
    ens = v["ensembles"]
    c = crit["criterio"]
    ini, fim = v["study_period"].split(" to ")
    hoje = date.today().strftime("%d/%m/%Y")

    rank = sorted(ms, key=ms.get)
    smape_rows = " \\\\\n".join(
        f"{model_name(m)} & {br(ms[m])} & {v['cities_ranked_first_by_model'][m]}/{v['n_cities']}" for m in rank
    )
    base_rows = " \\\\\n".join(
        f"{CITY_PT[city]} & {model_name(r['best'])} & {br(r['relmae'], 3)} & {r['dm']} & não"
        for city, r in b["by_city"].items()
    )
    ex_rows = " \\\\\n".join(
        f"{CITY_PT[city]} & {br(r['relmae_timesfm'], 3)} & {br(r['relmae_best_raw'], 3)} ({model_name(r['best_raw'])}) & "
        f"{br(r['relmae_best_log'], 3)} ({model_name(r['best_log'])})"
        for city, r in ex["per_city"].items()
    )
    mr = ex["mean_relmae"]
    iv_tfm_a, iv_tfm_l = iv["absolute"]["timesfm"], iv["log1p"]["timesfm"]
    best_rwis_a = min(iv["absolute"], key=lambda m: iv["absolute"][m]["rwis"])
    best_rwis_l = min(iv["log1p"], key=lambda m: iv["log1p"][m]["rwis"])
    em = ens["mean_by_approach"]

    return rf"""
\documentclass[aspectratio=169,11pt]{{beamer}}
\usepackage{{fontspec}}
\usepackage{{booktabs}}
\usepackage{{tikz}}
\usetikzlibrary{{positioning,arrows.meta}}
\usetheme{{default}}
\setbeamertemplate{{navigation symbols}}{{}}
\setbeamertemplate{{footline}}[frame number]
\definecolor{{az}}{{HTML}}{{2A78D6}}
\definecolor{{la}}{{HTML}}{{EB6834}}
\definecolor{{ci}}{{HTML}}{{52514E}}
\setbeamercolor{{frametitle}}{{fg=az}}
\setbeamercolor{{title}}{{fg=az}}
\setbeamerfont{{frametitle}}{{series=\bfseries}}
\graphicspath{{{{{PAPER / 'figures'}/}}}}
\tikzset{{box/.style={{draw=az,rounded corners,fill=az!8,align=center,font=\footnotesize,minimum height=1.05cm,text width=2.3cm}},
          arr/.style={{-Stealth,thick,ci}}}}

\title{{Previsão de dengue em 8 capitais}}
\subtitle{{TimesFM zero-shot contra modelos treinados por cidade: pipeline, resultados e próximos passos}}
\author{{Fabiano Novaes Barcellos Filho, José Trajano, Wilson Falco, Alexandre Chiavegatto Filho}}
\date{{Estado em {hoje}. Números gerados pelo pipeline (paper/verified\_numbers.json)}}

\begin{{document}}

\begin{{frame}}
\titlepage
\end{{frame}}

\begin{{frame}}{{O que ficou definido}}
\begin{{itemize}}
\item \textbf{{Repositório oficial:}} \texttt{{dengue-time-series}} (projeto DFP). O outro repositório (\texttt{{dengue-timeseries-skforecast}}) foi arquivado; as correções dele vieram para cá.
\item \textbf{{Revista-alvo:}} PLOS Neglected Tropical Diseases (a versão RSBMT fica como histórico).
\item \textbf{{Autores:}} Fabiano (correspondente), José, Wilson e Alexandre (orientador). Sem financiamento.
\item \textbf{{Conclusão principal (confirmatória):}} nenhum modelo bate o naive sazonal pelo critério pré-registrado, em {b['cities_where_any_model_beats_baseline']} de {b['cities_total']} cidades.
\item \textbf{{Leitura do TimesFM:}} comparável aos melhores modelos treinados, não superior.
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{Dados}}
\begin{{columns}}[T]
\column{{0.42\textwidth}}
\begin{{itemize}}\small
\item InfoDengue (Fiocruz/FGV): casos notificados por semana epidemiológica, agregados por mês
\item {v['n_cities']} capitais das 5 regiões
\item {v['n_months_per_city']} meses por cidade ({ini} a {fim})
\item População do IBGE ancorada nos Censos 2010 e 2022
\end{{itemize}}
\column{{0.56\textwidth}}
\centering\includegraphics[height=0.78\textheight,width=\linewidth,keepaspectratio]{{fig1_series.png}}
\end{{columns}}
\end{{frame}}

\begin{{frame}}{{Pipeline}}
\centering
\begin{{tikzpicture}}[node distance=0.45cm]
\node[box] (d) {{Séries mensais\\{v['n_cities']} cidades}};
\node[box,right=of d] (r) {{Origem móvel\\treino $\geq$ {v['min_train_size']} meses\\horizonte {v['horizon_months']}}};
\node[box,right=of r] (m) {{{v['n_models']} modelos\\+ naive sazonal\\+ 5 globais}};
\node[box,right=of m] (p) {{{br(v['n_predictions_per_model_city'], 0)} previsões\\por modelo e cidade}};
\node[box,below=0.9cm of p] (u) {{Bootstrap por janela\\+ Diebold-Mariano}};
\node[box,left=of u] (c) {{Critério\\pré-registrado}};
\node[box,left=of c] (i) {{Intervalos\\conformais}};
\node[box,left=of i] (e) {{Ensembles}};
\draw[arr] (d)--(r); \draw[arr] (r)--(m); \draw[arr] (m)--(p); \draw[arr] (p)--(u); \draw[arr] (u)--(c);
\draw[arr] (p.south west)--(i.north); \draw[arr] (p.south west)--(e.north);
\end{{tikzpicture}}

\vspace{{0.4cm}}
\small {v['n_folds_per_city']} janelas por cidade, {br(v['n_predictions_total'], 0)} previsões no total. Modelos treinados: SARIMAX, Ridge, LightGBM, XGBoost, CatBoost e Random Forest (skforecast, 24 lags). TimesFM 2.5 sem treino nenhum.
\end{{frame}}

\begin{{frame}}{{Critério pré-registrado (LAB-135)}}
\begin{{itemize}}
\item Fixado em {crit['fixado_em']} no \texttt{{results/criterion.json}}, minutos antes da primeira execução do teste
\item Métrica: \textbf{{RelMAE}}, o MAE do modelo dividido pelo MAE do naive sazonal na mesma cidade e janelas
\item Bootstrap pareado por janela inteira (B = {br(crit['bootstrap']['B'], 0)})
\item Diebold-Mariano com correção de Harvey: p $<$ {br(c['alpha'], 2)} em pelo menos {c['min_horizontes']} de {c['n_horizontes']} horizontes
\item Confirmado = IC exclui zero \textbf{{e}} DM passa. sMAPE entra como sensibilidade
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{Acurácia entre os modelos (sMAPE)}}
\begin{{columns}}[T]
\column{{0.42\textwidth}}
\footnotesize
\begin{{tabular}}{{@{{}}lrr@{{}}}}
\toprule
Modelo & sMAPE (\%) & 1º lugar \\
\midrule
{smape_rows} \\
\bottomrule
\end{{tabular}}

\vspace{{0.2cm}}\footnotesize
Com os 5 modelos globais na comparação, o TimesFM fica em 1º em {g['timesfm_wins_with_global_pool']} de {g['n_cities']} cidades, não em {g['timesfm_wins_published_pool']}.
\column{{0.56\textwidth}}
\includegraphics[width=\linewidth]{{fig2_heatmap.png}}
\end{{columns}}
\end{{frame}}

\begin{{frame}}{{Resultado confirmatório: ninguém bate o naive sazonal}}
\begin{{columns}}[T]
\column{{0.55\textwidth}}
\scriptsize
\begin{{tabular}}{{@{{}}llrrl@{{}}}}
\toprule
Cidade & Melhor & RelMAE & DM & Bate? \\
\midrule
{base_rows} \\
\bottomrule
\end{{tabular}}
\column{{0.43\textwidth}}
\includegraphics[width=\linewidth]{{fig10_baseline.png}}
\end{{columns}}
\vspace{{0.15cm}}\small
O ponto estimado favorece o melhor modelo em todas as cidades (RelMAE {br(b['relmae_range'][0], 3)} a {br(b['relmae_range'][1], 3)}), mas o DM passa em no máximo {b['max_dm_horizons']} de 12 horizontes.
\end{{frame}}

\begin{{frame}}{{O erro depende do horizonte}}
\begin{{columns}}[T]
\column{{0.4\textwidth}}
\begin{{itemize}}\small
\item sMAPE do TimesFM: {br(h['h1'])}\% a 1 mês, {br(h['h3'])}\% a 3, {br(h['h6'])}\% a 6 e {br(h['h12'])}\% a 12
\item {h['share_of_degradation_by_h6']}\% da piora acontece até o 6º mês
\item A média de 12 meses descreve mal os dois regimes
\end{{itemize}}
\column{{0.58\textwidth}}
\includegraphics[width=\linewidth]{{fig9_horizon.png}}
\end{{columns}}
\end{{frame}}

\begin{{frame}}{{Análise exploratória: modelos treinados em escala log}}
\footnotesize
Emenda de 04/10, feita \textbf{{depois}} de ver resultados: não substitui o veredito confirmatório. Árvores na contagem bruta não preveem acima do máximo do treino.

\vspace{{0.15cm}}
\begin{{tabular}}{{lrll}}
\toprule
Cidade & TimesFM & Melhor treinado, bruto & Melhor treinado, log \\
\midrule
{ex_rows} \\
\bottomrule
\end{{tabular}}

\vspace{{0.15cm}}
RelMAE médio: TimesFM {br(mr['timesfm'], 3)}; CatBoost log {br(mr['catboost_log'], 3)} (bruto {br(mr['catboost'], 3)}). Diferença TimesFM contra log confirmada em {ex['timesfm_vs_log_confirmed']} de {ex['timesfm_vs_log_pairs']} pares, {ex['timesfm_vs_catboost_log_confirmed']} contra o CatBoost. Nenhum modelo em log bate o naive ({ex['cities_where_any_model_beats_baseline']} de {v['n_cities']}).
\end{{frame}}

\begin{{frame}}{{Intervalos e combinações}}
\begin{{itemize}}\small
\item Intervalos conformais do TimesFM: cobertura de {br(100 * iv_tfm_a['c95'])}\% (construção absoluta) e {br(100 * iv_tfm_l['c95'])}\% (log) para 95\% nominal
\item O ranking probabilístico (WIS) muda com a construção: o melhor é {model_name(best_rwis_a)} numa e {model_name(best_rwis_l)} na outra. Não há ranking probabilístico robusto
\item Ensembles: sMAPE médio da mediana {br(em['median']['sMAPE'])}\% contra {br(em['timesfm']['sMAPE'])}\% do TimesFM sozinho; o ensemble bate o melhor membro em {ens['n_cities_ensemble_beats_best_member']} de 8 cidades
\end{{itemize}}
\end{{frame}}

\begin{{frame}}{{Onde preciso do apoio de vocês}}
\begin{{enumerate}}
\item \textbf{{Afiliação:}} José e Wilson, preencher a sua no .docx de revisão (campos em vermelho \texttt{{[PENDING]}})
\item \textbf{{Enquadramento:}} revisar a seção exploratória (escala log) e a leitura ``comparável, não superior''
\item \textbf{{Código:}} opinar entre abrir o repositório ou depositar no Zenodo com DOI
\item \textbf{{Texto:}} comentários no .docx, com controle de alterações
\item \textbf{{Aprovação}} para seguirmos com a versão de submissão no template da PLOS NTD
\end{{enumerate}}
\end{{frame}}

\end{{document}}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / f"DFP_deck_pipeline_{date.today().isoformat()}.pdf"))
    args = ap.parse_args()
    v = json.loads((PAPER / "verified_numbers.json").read_text(encoding="utf-8"))
    crit = json.loads((ROOT / "results" / "criterion.json").read_text(encoding="utf-8"))
    work = ROOT / "build" / "deck"
    work.mkdir(parents=True, exist_ok=True)
    tex = work / "deck_pipeline.tex"
    tex.write_text(build(v, crit), encoding="utf-8")
    r = subprocess.run([TECTONIC, "-X", "compile", tex.name], cwd=work, capture_output=True, text=True)
    (work / "compile.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-2500:])
        raise SystemExit("tectonic falhou")
    out = Path(args.out)
    shutil.copy(work / "deck_pipeline.pdf", out)
    print(f"escrito {out}")


if __name__ == "__main__":
    main()
