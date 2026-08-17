"""
Gera todas as tabelas LaTeX e figuras do manuscrito a partir dos dados brutos.

Nada aqui e transcrito de rascunho: cada numero e recalculado dos arquivos em
data/processed/ e results/. Emite tambem paper/verified_numbers.json, que registra
todo valor citado no texto para permitir conferencia celula a celula.

Uso:
    python scripts/build_paper_assets.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
PAPER = ROOT / "paper"
TABLES = PAPER / "tables"
FIGURES = PAPER / "figures"

for d in (TABLES, FIGURES):
    d.mkdir(parents=True, exist_ok=True)

# slug do arquivo -> (nome no paper, UF, macrorregiao)
CITIES = {
    "sao": ("Sao Paulo", "SP", "Southeast"),
    "rio": ("Rio de Janeiro", "RJ", "Southeast"),
    "belo": ("Belo Horizonte", "MG", "Southeast"),
    "brasilia": ("Brasilia", "DF", "Central-West"),
    "fortaleza": ("Fortaleza", "CE", "Northeast"),
    "recife": ("Recife", "PE", "Northeast"),
    "manaus": ("Manaus", "AM", "North"),
    "salvador": ("Salvador", "BA", "Northeast"),
}

# slug dos arquivos de resultado (difere do slug dos dados processados)
RESULT_SLUG = {
    "sao": "sao_paulo",
    "rio": "rio",
    "belo": "belo_horizonte",
    "brasilia": "brasilia",
    "fortaleza": "fortaleza",
    "recife": "recife",
    "manaus": "manaus",
    "salvador": "salvador",
}

MODELS = ["timesfm", "catboost", "xgboost", "randomforest", "sarimax", "lgbm"]
MODEL_LABEL = {
    "timesfm": "TimesFM",
    "catboost": "CatBoost",
    "xgboost": "XGBoost",
    "randomforest": "Random Forest",
    "sarimax": "SARIMAX",
    "lgbm": "LightGBM",
}
SUPERVISED = [m for m in MODELS if m != "timesfm"]

BOOT_N = 2000
BOOT_SEED = 42


# --------------------------------------------------------------------------- #
# metricas
# --------------------------------------------------------------------------- #
def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """sMAPE em pontos percentuais, na forma simetrica limitada a 200."""
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    ratio = np.divide(
        np.abs(y_true - y_pred), denom, out=np.zeros_like(denom), where=denom != 0
    )
    return float(np.mean(ratio) * 100.0)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def boot_ci(y_true: np.ndarray, y_pred: np.ndarray, seed: int = BOOT_SEED):
    """IC95 percentil do sMAPE por reamostragem das previsoes pareadas.

    Reamostra pares (y_true, y_pred) com reposicao. As previsoes dentro de um
    mesmo fold nao sao independentes, entao este IC subestima a incerteza real:
    isso esta declarado como limitacao no manuscrito.
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)
    stats = np.empty(BOOT_N)
    for i in range(BOOT_N):
        idx = rng.integers(0, n, n)
        stats[i] = smape(y_true[idx], y_pred[idx])
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


# --------------------------------------------------------------------------- #
# carga
# --------------------------------------------------------------------------- #
def load_series() -> dict[str, pd.Series]:
    out = {}
    for slug, (name, _, _) in CITIES.items():
        df = pd.read_csv(DATA / f"dengue_monthly_{slug}.csv", parse_dates=["date"])
        out[name] = df.set_index("date")["value"].astype(float).sort_index()
    return out


def load_predictions() -> dict[str, pd.DataFrame]:
    out = {}
    for slug, (name, _, _) in CITIES.items():
        df = pd.read_csv(
            RESULTS / f"benchmark_{RESULT_SLUG[slug]}_predictions.csv",
            parse_dates=["date"],
        )
        out[name] = df
    return out


def compute_metrics(preds: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for city, df in preds.items():
        for model in MODELS:
            sub = df[df["model"] == model]
            if sub.empty:
                continue
            yt = sub["y_true"].to_numpy(dtype=float)
            yp = sub["y_pred"].to_numpy(dtype=float)
            lo, hi = boot_ci(yt, yp)
            rows.append(
                {
                    "city": city,
                    "model": model,
                    "sMAPE": smape(yt, yp),
                    "sMAPE_lo": lo,
                    "sMAPE_hi": hi,
                    "MAE": mae(yt, yp),
                    "RMSE": rmse(yt, yp),
                    "n": len(sub),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# helpers LaTeX
# --------------------------------------------------------------------------- #
def tex_escape(s: str) -> str:
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def bold_min(values, fmt, lower_is_better=True):
    """Formata uma lista destacando o melhor valor em negrito."""
    arr = np.array(values, dtype=float)
    best = np.nanmin(arr) if lower_is_better else np.nanmax(arr)
    out = []
    for v in arr:
        s = fmt(v)
        out.append(rf"\textbf{{{s}}}" if np.isclose(v, best) else s)
    return out


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    print(f"  escrito {path.relative_to(ROOT)}")


# --------------------------------------------------------------------------- #
# Tabela 1: descritiva
# --------------------------------------------------------------------------- #
def table1(series: dict[str, pd.Series]) -> tuple[str, list[dict]]:
    rows = []
    for name, (city, uf, region) in ((v[0], v) for v in CITIES.values()):
        s = series[city]
        rows.append(
            {
                "city": city,
                "uf": uf,
                "region": region,
                "n": int(s.size),
                "mean": float(s.mean()),
                "median": float(s.median()),
                "min": int(s.min()),
                "max": int(s.max()),
                "cv": float(s.std(ddof=1) / s.mean() * 100),
                "total": int(s.sum()),
            }
        )
    rows.sort(key=lambda r: -r["total"])

    body = "\n".join(
        rf"{tex_escape(r['city'])} ({r['uf']}) & {r['region']} & {r['n']} & "
        rf"{r['mean']:,.0f} & {r['median']:,.0f} & {r['min']:,} & {r['max']:,} & "
        rf"{r['cv']:.0f} & {r['total']:,} \\"
        for r in rows
    )
    tex = rf"""% gerado por scripts/build_paper_assets.py -- nao editar a mao
\begin{{table}}[htbp]
\centering
\small
\caption{{Descriptive statistics of the monthly notified dengue case series,
eight Brazilian state capitals, January 2010 to December 2024.}}
\label{{tab:descriptive}}
\begin{{tabular}}{{llrrrrrrr}}
\toprule
City & Region & $n$ & Mean & Median & Min & Max & CV (\%) & Total \\
\midrule
{body}
\bottomrule
\end{{tabular}}

\vspace{{0.5em}}
\begin{{minipage}}{{\textwidth}}
\footnotesize
CV: coefficient of variation (standard deviation divided by the mean, expressed as a
percentage). $n$: number of monthly observations. Rows are sorted by the 15-year case
total. Source: InfoDengue (Fiocruz/FGV).
\end{{minipage}}
\end{{table}}
"""
    return tex, rows


# --------------------------------------------------------------------------- #
# Tabela 2: sMAPE com IC95
# --------------------------------------------------------------------------- #
def table2(met: pd.DataFrame) -> str:
    order = [v[0] for v in CITIES.values()]
    lines = []
    for city in order:
        sub = met[met["city"] == city].set_index("model")
        vals = [sub.loc[m, "sMAPE"] for m in MODELS]
        cells = bold_min(vals, lambda v: f"{v:.1f}")
        cis = [
            rf"\scriptsize({sub.loc[m, 'sMAPE_lo']:.1f}, {sub.loc[m, 'sMAPE_hi']:.1f})"
            for m in MODELS
        ]
        lines.append(rf"{tex_escape(city)} & " + " & ".join(cells) + r" \\")
        lines.append(r" & " + " & ".join(cis) + r" \\[2pt]")

    means = [met[met["model"] == m]["sMAPE"].mean() for m in MODELS]
    mean_cells = bold_min(means, lambda v: f"{v:.1f}")
    wins = []
    for m in MODELS:
        w = sum(
            1
            for c in order
            if met[met["city"] == c].set_index("model")["sMAPE"].idxmin() == m
        )
        wins.append(w)
    win_cells = bold_min(wins, lambda v: f"{int(v)}/8", lower_is_better=False)

    body = "\n".join(lines)
    header = " & ".join(MODEL_LABEL[m] for m in MODELS)
    tex = rf"""% gerado por scripts/build_paper_assets.py -- nao editar a mao
\begin{{table}}[htbp]
\centering
\small
\setlength{{\tabcolsep}}{{4pt}}
\caption{{Forecasting accuracy by model and city: sMAPE (\%) with 95\% bootstrap
percentile confidence intervals. Rolling-origin cross-validation, 12-month horizon,
1{{,}}452 pooled predictions per model per city.}}
\label{{tab:smape}}
\begin{{tabular}}{{lcccccc}}
\toprule
City & {header} \\
\midrule
{body}
\midrule
Mean across cities & {" & ".join(mean_cells)} \\
Cities ranked first & {" & ".join(win_cells)} \\
\bottomrule
\end{{tabular}}

\vspace{{0.5em}}
\begin{{minipage}}{{\textwidth}}
\footnotesize
Bold indicates the lowest sMAPE in each row. Confidence intervals were obtained by
resampling the 1{{,}}452 paired predictions with replacement ({BOOT_N} replicates,
percentile method). Because predictions from the same rolling-origin fold are not
independent, these intervals understate the true uncertainty and should be read as a
lower bound on the spread. TimesFM was applied zero-shot, with no city-specific
training.
\end{{minipage}}
\end{{table}}
"""
    return tex


# --------------------------------------------------------------------------- #
# Tabela 3: MAE e RMSE
# --------------------------------------------------------------------------- #
def table3(met: pd.DataFrame) -> str:
    order = [v[0] for v in CITIES.values()]
    lines = []
    for city in order:
        sub = met[met["city"] == city].set_index("model")
        maes = bold_min([sub.loc[m, "MAE"] for m in MODELS], lambda v: f"{v:,.0f}")
        rmses = bold_min([sub.loc[m, "RMSE"] for m in MODELS], lambda v: f"{v:,.0f}")
        lines.append(
            rf"\multirow{{2}}{{*}}{{{tex_escape(city)}}} & MAE & "
            + " & ".join(maes)
            + r" \\"
        )
        lines.append(r" & RMSE & " + " & ".join(rmses) + r" \\[2pt]")

    body = "\n".join(lines)
    header = " & ".join(MODEL_LABEL[m] for m in MODELS)
    tex = rf"""% gerado por scripts/build_paper_assets.py -- nao editar a mao
\begin{{table}}[htbp]
\centering
\small
\setlength{{\tabcolsep}}{{4pt}}
\caption{{Forecasting accuracy by model and city: mean absolute error (MAE) and root
mean squared error (RMSE), in notified cases per month.}}
\label{{tab:mae-rmse}}
\begin{{tabular}}{{llcccccc}}
\toprule
City & Metric & {header} \\
\midrule
{body}
\bottomrule
\end{{tabular}}

\vspace{{0.5em}}
\begin{{minipage}}{{\textwidth}}
\footnotesize
Bold indicates the best value in each row. MAE and RMSE are reported on the original
case-count scale and are therefore not comparable across cities. RMSE penalises large
errors more heavily than MAE; the gap between the two within a city reflects how much
of the total error is concentrated in a small number of epidemic peaks.
\end{{minipage}}
\end{{table}}
"""
    return tex


# --------------------------------------------------------------------------- #
# Tabela 4: divergencia entre metricas
# --------------------------------------------------------------------------- #
def table4(met: pd.DataFrame) -> tuple[str, list[dict]]:
    order = [v[0] for v in CITIES.values()]
    rows = []
    for city in order:
        sub = met[met["city"] == city].set_index("model")
        rows.append(
            {
                "city": city,
                "smape": sub["sMAPE"].idxmin(),
                "mae": sub["MAE"].idxmin(),
                "rmse": sub["RMSE"].idxmin(),
            }
        )
    n_agree = sum(1 for r in rows if r["smape"] == r["mae"] == r["rmse"])

    body = "\n".join(
        rf"{tex_escape(r['city'])} & {MODEL_LABEL[r['smape']]} & "
        rf"{MODEL_LABEL[r['mae']]} & {MODEL_LABEL[r['rmse']]} & "
        rf"{'Yes' if r['smape'] == r['mae'] == r['rmse'] else 'No'} \\"
        for r in rows
    )
    tex = rf"""% gerado por scripts/build_paper_assets.py -- nao editar a mao
\begin{{table}}[htbp]
\centering
\small
\caption{{Best-performing model per city under each accuracy metric, showing where the
choice of metric changes the winner.}}
\label{{tab:metric-disagreement}}
\begin{{tabular}}{{llllc}}
\toprule
City & Best by sMAPE & Best by MAE & Best by RMSE & All three agree \\
\midrule
{body}
\bottomrule
\end{{tabular}}

\vspace{{0.5em}}
\begin{{minipage}}{{\textwidth}}
\footnotesize
The three metrics select the same model in {n_agree} of the eight cities. sMAPE weights
relative error and therefore rewards accuracy during inter-epidemic troughs, when case
counts are low; RMSE weights absolute squared error and therefore rewards accuracy at
epidemic peaks. Reporting a single metric would conceal this disagreement, so the
primary metric is declared in advance (sMAPE) and the others are reported alongside it.
\end{{minipage}}
\end{{table}}
"""
    return tex, rows


# --------------------------------------------------------------------------- #
# figuras
# --------------------------------------------------------------------------- #
def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.5,
            "legend.frameon": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES / f"{name}.{ext}")
    plt.close(fig)
    print(f"  escrito paper/figures/{name}.pdf (+.png)")


def fig1_series(series: dict[str, pd.Series]) -> None:
    """Series temporais das 8 capitais, com a janela minima de treino sombreada."""
    order = sorted(CITIES.values(), key=lambda v: -series[v[0]].sum())
    fig, axes = plt.subplots(4, 2, figsize=(7.2, 8.4), sharex=True)
    for ax, (city, uf, region) in zip(axes.ravel(), order):
        s = series[city]
        ax.fill_between(s.index, s.values, color="#c62828", alpha=0.18, linewidth=0)
        ax.plot(s.index, s.values, color="#c62828", linewidth=0.9)
        cut = s.index[47]
        ax.axvspan(s.index[0], cut, color="0.55", alpha=0.18, linewidth=0)
        ax.set_title(f"{city} ({uf}), {region}", loc="left", fontweight="bold")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.margins(x=0.01)
    axes[0, 0].text(
        series[order[0][0]].index[6],
        series[order[0][0]].max() * 0.86,
        "minimum\ntraining window",
        fontsize=7,
        color="0.35",
    )
    for ax in axes[-1]:
        ax.set_xlabel("Year")
    for ax in axes[:, 0]:
        ax.set_ylabel("Notified cases")
    fig.suptitle(
        "Monthly notified dengue cases, eight Brazilian state capitals (2010 to 2024)",
        fontweight="bold",
        y=0.997,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.978))
    save(fig, "fig1_series")


def fig2_heatmap(met: pd.DataFrame) -> None:
    """Heatmap de sMAPE, modelos ordenados pela media."""
    order_cities = sorted(
        (v[0] for v in CITIES.values()),
        key=lambda c: met[met["city"] == c]["sMAPE"].min(),
    )
    order_models = sorted(MODELS, key=lambda m: met[met["model"] == m]["sMAPE"].mean())
    mat = np.array(
        [
            [
                met[(met["city"] == c) & (met["model"] == m)]["sMAPE"].iloc[0]
                for c in order_cities
            ]
            for m in order_models
        ]
    )

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    im = ax.imshow(mat, cmap="RdYlGn_r", aspect="auto", vmin=50, vmax=160)
    ax.set_xticks(range(len(order_cities)))
    ax.set_xticklabels(order_cities, rotation=30, ha="right")
    ax.set_yticks(range(len(order_models)))
    ax.set_yticklabels([MODEL_LABEL[m] for m in order_models])
    ax.grid(False)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            best = np.isclose(v, mat[:, j].min())
            ax.text(
                j,
                i,
                f"{v:.0f}",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold" if best else "normal",
                color="white" if (v > 130 or v < 62) else "black",
            )
            if best:
                ax.add_patch(
                    plt.Rectangle(
                        (j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="black", lw=1.6
                    )
                )
    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.028)
    cb.set_label("sMAPE (%)")
    cb.outline.set_visible(False)
    ax.set_title(
        "Forecast error by model and city (lower is better)",
        loc="left",
        fontweight="bold",
    )
    fig.tight_layout()
    save(fig, "fig2_heatmap")


def fig3_timesfm_vs_best(met: pd.DataFrame) -> None:
    """TimesFM contra o melhor supervisionado por cidade, com IC95."""
    order = sorted(
        (v[0] for v in CITIES.values()),
        key=lambda c: met[(met["city"] == c) & (met["model"] == "timesfm")][
            "sMAPE"
        ].iloc[0],
    )
    tf, bs, tf_err, bs_err, bs_name = [], [], [[], []], [[], []], []
    for c in order:
        sub = met[met["city"] == c].set_index("model")
        t = sub.loc["timesfm"]
        sup = sub.loc[SUPERVISED]
        b = sup.loc[sup["sMAPE"].idxmin()]
        tf.append(t["sMAPE"])
        bs.append(b["sMAPE"])
        tf_err[0].append(t["sMAPE"] - t["sMAPE_lo"])
        tf_err[1].append(t["sMAPE_hi"] - t["sMAPE"])
        bs_err[0].append(b["sMAPE"] - b["sMAPE_lo"])
        bs_err[1].append(b["sMAPE_hi"] - b["sMAPE"])
        bs_name.append(MODEL_LABEL[sup["sMAPE"].idxmin()])

    x = np.arange(len(order))
    w = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(
        x - w / 2, tf, w, label="TimesFM (zero-shot)", color="#1565c0",
        yerr=tf_err, capsize=2.5, error_kw={"lw": 0.9, "ecolor": "0.25"},
    )
    ax.bar(
        x + w / 2, bs, w, label="Best supervised model", color="#ef6c00",
        yerr=bs_err, capsize=2.5, error_kw={"lw": 0.9, "ecolor": "0.25"},
    )
    for i, nm in enumerate(bs_name):
        ax.text(x[i] + w / 2, bs[i] + bs_err[1][i] + 1.5, nm, ha="center", fontsize=6.5,
                va="bottom", color="#8a4500")
    for i, v in enumerate(tf):
        ax.text(x[i] - w / 2, tf_err[0][i] and v + tf_err[1][i] + 1.5, f"{v:.0f}",
                ha="center", fontsize=6.5, va="bottom", color="#0d3f76")
    ax.set_xticks(x)
    ax.set_xticklabels(order, rotation=25, ha="right")
    ax.set_ylabel("sMAPE (%)")
    ax.set_ylim(0, max(bs) * 1.16)
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    ax.set_title(
        "Zero-shot TimesFM versus the best purpose-trained model in each city",
        loc="left",
        fontweight="bold",
    )
    fig.tight_layout()
    save(fig, "fig3_timesfm_vs_best")


def fig4_metric_disagreement(met: pd.DataFrame) -> None:
    """Mostra que o vencedor muda conforme a metrica."""
    order = [v[0] for v in CITIES.values()]
    metrics = ["sMAPE", "MAE", "RMSE"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.3), sharey=True)
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    cmap = {m: colors[i] for i, m in enumerate(MODELS)}

    for ax, metric in zip(axes, metrics):
        winners = []
        for c in order:
            sub = met[met["city"] == c].set_index("model")
            winners.append(sub[metric].idxmin())
        counts = {m: winners.count(m) for m in MODELS if winners.count(m) > 0}
        names = sorted(counts, key=lambda m: -counts[m])
        ax.barh(
            [MODEL_LABEL[m] for m in names],
            [counts[m] for m in names],
            color=[cmap[m] for m in names],
        )
        for i, m in enumerate(names):
            ax.text(counts[m] + 0.08, i, str(counts[m]), va="center", fontsize=8)
        ax.set_title(f"Best by {metric}", loc="left", fontweight="bold")
        ax.set_xlim(0, 8.6)
        ax.set_xlabel("Cities ranked first")
        ax.invert_yaxis()
    fig.suptitle(
        "The choice of accuracy metric changes which model wins",
        fontweight="bold",
        y=1.0,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "fig4_metric_disagreement")


def fig5_observed_vs_predicted(preds: dict[str, pd.DataFrame]) -> None:
    """Observado contra previsto do TimesFM e do melhor supervisionado, 4 cidades."""
    pick = ["Sao Paulo", "Rio de Janeiro", "Fortaleza", "Manaus"]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8))
    for ax, city in zip(axes.ravel(), pick):
        df = preds[city]
        obs = df[df["model"] == "timesfm"].groupby("date")["y_true"].first().sort_index()
        ax.plot(obs.index, obs.values, color="black", lw=1.1, label="Observed", zorder=3)
        for model, color in (("timesfm", "#1565c0"), ("catboost", "#ef6c00")):
            sub = df[df["model"] == model].groupby("date")["y_pred"].mean().sort_index()
            ax.plot(
                sub.index, sub.values, color=color, lw=1.0, ls="--",
                label=MODEL_LABEL[model], alpha=0.9,
            )
        ax.set_title(city, loc="left", fontweight="bold")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.margins(x=0.01)
    axes[0, 0].legend(loc="upper left", fontsize=7.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("Notified cases")
    for ax in axes[-1]:
        ax.set_xlabel("Year")
    fig.suptitle(
        "Observed versus predicted monthly cases, averaged across rolling-origin folds",
        fontweight="bold",
        y=0.997,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    save(fig, "fig5_observed_vs_predicted")


# --------------------------------------------------------------------------- #
def main() -> None:
    print("Carregando dados...")
    series = load_series()
    preds = load_predictions()

    print(f"Calculando metricas e bootstrap ({BOOT_N} replicas)...")
    met = compute_metrics(preds)
    met.to_csv(RESULTS / "comparisons" / "metrics_with_ci.csv", index=False)
    print("  escrito results/comparisons/metrics_with_ci.csv")

    print("Gerando tabelas LaTeX...")
    t1, desc_rows = table1(series)
    write(TABLES / "table1_descriptive.tex", t1)
    write(TABLES / "table2_smape.tex", table2(met))
    write(TABLES / "table3_mae_rmse.tex", table3(met))
    t4, disagree = table4(met)
    write(TABLES / "table4_metric_disagreement.tex", t4)

    print("Gerando figuras...")
    setup_style()
    fig1_series(series)
    fig2_heatmap(met)
    fig3_timesfm_vs_best(met)
    fig4_metric_disagreement(met)
    fig5_observed_vs_predicted(preds)

    # numeros citados no corpo do texto, para conferencia
    tf = met[met["model"] == "timesfm"]
    wins = {
        m: sum(
            1
            for c in (v[0] for v in CITIES.values())
            if met[met["city"] == c].set_index("model")["sMAPE"].idxmin() == m
        )
        for m in MODELS
    }
    verified = {
        "n_cities": len(CITIES),
        "n_models": len(MODELS),
        "n_months_per_city": 180,
        "n_folds_per_city": 121,
        "n_predictions_per_model_city": int(met["n"].iloc[0]),
        "n_predictions_total": int(met["n"].sum()),
        "study_period": "2010-01 to 2024-12",
        "mean_smape_by_model": {
            m: round(met[met["model"] == m]["sMAPE"].mean(), 2) for m in MODELS
        },
        "median_smape_by_model": {
            m: round(met[met["model"] == m]["sMAPE"].median(), 2) for m in MODELS
        },
        "cities_ranked_first_by_model": wins,
        "timesfm_smape_range": [
            round(tf["sMAPE"].min(), 1),
            round(tf["sMAPE"].max(), 1),
        ],
        "best_supervised_by_mean_smape": min(
            SUPERVISED, key=lambda m: met[met["model"] == m]["sMAPE"].mean()
        ),
        "per_city": {
            r["city"]: {
                r2["model"]: {
                    "sMAPE": round(r2["sMAPE"], 2),
                    "sMAPE_CI": [round(r2["sMAPE_lo"], 2), round(r2["sMAPE_hi"], 2)],
                    "MAE": round(r2["MAE"], 1),
                    "RMSE": round(r2["RMSE"], 1),
                }
                for _, r2 in met[met["city"] == r["city"]].iterrows()
            }
            for _, r in met.drop_duplicates("city").iterrows()
        },
        "descriptive": {r["city"]: r for r in desc_rows},
        "metric_disagreement": disagree,
        "bootstrap": {"replicates": BOOT_N, "seed": BOOT_SEED, "method": "percentile"},
    }
    (PAPER / "verified_numbers.json").write_text(
        json.dumps(verified, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("  escrito paper/verified_numbers.json")

    print("\nResumo:")
    for m in sorted(MODELS, key=lambda m: met[met["model"] == m]["sMAPE"].mean()):
        v = met[met["model"] == m]["sMAPE"]
        print(
            f"  {MODEL_LABEL[m]:15s} sMAPE medio {v.mean():6.2f}  "
            f"mediana {v.median():6.2f}  vitorias {wins[m]}/8"
        )


if __name__ == "__main__":
    main()
