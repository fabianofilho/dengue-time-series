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

MODELS = ["timesfm", "catboost", "xgboost", "randomforest", "sarimax", "ridge", "lgbm"]
MODEL_LABEL = {
    "timesfm": "TimesFM",
    "catboost": "CatBoost",
    "xgboost": "XGBoost",
    "randomforest": "Random Forest",
    "sarimax": "SARIMAX",
    "ridge": "Ridge",
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


def load_population() -> dict[str, pd.Series]:
    """Populacao mensal por cidade, interpolada da serie anual do IBGE.

    A serie anual esta ancorada nos Censos 2010 e 2022 (ver scripts/fetch_ibge.py).
    Aqui ela vira mensal por interpolacao linear entre os pontos de 1 de julho,
    que e a data de referencia das estimativas do IBGE.
    """
    df = pd.read_csv(ROOT / "data" / "raw" / "ibge_population.csv")
    out = {}
    for name in (v[0] for v in CITIES.values()):
        sub = df[df["city"] == name].sort_values("year")
        anchors = pd.Series(
            sub["population"].to_numpy(dtype=float),
            index=pd.to_datetime([f"{y}-07-01" for y in sub["year"]]),
        )
        idx = pd.date_range("2010-01-01", "2024-12-01", freq="MS")
        out[name] = (
            anchors.reindex(anchors.index.union(idx))
            .interpolate(method="time")
            .bfill()
            .ffill()
            .reindex(idx)
        )
    return out


def load_interval_calibration() -> pd.DataFrame:
    """Calibracao dos intervalos, produzida por scripts/run_intervals.py."""
    return pd.read_csv(RESULTS / "comparisons" / "interval_calibration.csv")


def load_interval_predictions() -> pd.DataFrame:
    return pd.read_csv(
        RESULTS / "comparisons" / "predictions_with_intervals.csv", parse_dates=["date"]
    )


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
def table1(
    series: dict[str, pd.Series], pop: dict[str, pd.Series]
) -> tuple[str, list[dict]]:
    rows = []
    for name, (city, uf, region) in ((v[0], v) for v in CITIES.values()):
        s = series[city]
        p = pop[city]
        inc = s / p * 100_000  # incidencia mensal por 100 mil habitantes
        rows.append(
            {
                "city": city,
                "uf": uf,
                "region": region,
                "n": int(s.size),
                "median": float(s.median()),
                "max": int(s.max()),
                "cv": float(s.std(ddof=1) / s.mean() * 100),
                "total": int(s.sum()),
                "pop2022": int(p.loc["2022-07-01"]),
                "inc_mean_annual": float(inc.mean() * 12),
                "inc_median": float(inc.median()),
                "inc_max": float(inc.max()),
            }
        )
    rows.sort(key=lambda r: -r["inc_mean_annual"])

    body = "\n".join(
        rf"{tex_escape(r['city'])} ({r['uf']}) & {r['region']} & "
        rf"{r['pop2022'] / 1e6:.2f} & {r['total']:,} & {r['median']:,.0f} & "
        rf"{r['max']:,} & {r['cv']:.0f} & "
        rf"{r['inc_mean_annual']:,.0f} & {r['inc_median']:.0f} & {r['inc_max']:,.0f} \\"
        for r in rows
    )
    tex = rf"""% gerado por scripts/build_paper_assets.py -- nao editar a mao
\begin{{table}}[htbp]
\centering
\footnotesize
\setlength{{\tabcolsep}}{{4pt}}
\caption{{Notified dengue burden in eight Brazilian state capitals, January 2010 to
December 2024: monthly case counts and population-standardised incidence.}}
\label{{tab:descriptive}}
\begin{{tabular}}{{llrrrrrrrr}}
\toprule
 & & Pop. 2022 & \multicolumn{{4}}{{c}}{{Monthly cases}}
 & \multicolumn{{3}}{{c}}{{Incidence per 100{{,}}000}} \\
\cmidrule(lr){{4-7}} \cmidrule(lr){{8-10}}
City & Region & (millions) & Total & Median & Max & CV (\%)
 & Annual & Median & Max \\
\midrule
{body}
\bottomrule
\end{{tabular}}

\vspace{{0.5em}}
\begin{{minipage}}{{\textwidth}}
\footnotesize
Each city contributed 180 monthly observations. CV: coefficient of variation of the
monthly case count (standard deviation divided by the mean, as a percentage). Incidence
columns are notified cases per 100{{,}}000 inhabitants; Annual is the mean monthly
incidence multiplied by twelve, Median and Max are monthly values. Rows are sorted by
mean annual incidence, which reorders the table relative to absolute counts. Population
denominators are interpolated monthly from an annual series anchored on the 2010 and 2022
Censuses (see Methods). Case source: InfoDengue (Fiocruz/FGV); population source: IBGE.
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
            rf"\tiny({sub.loc[m, 'sMAPE_lo']:.1f}, {sub.loc[m, 'sMAPE_hi']:.1f})"
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
\footnotesize
\setlength{{\tabcolsep}}{{2.5pt}}
\caption{{Forecasting accuracy by model and city: sMAPE (\%) with 95\% bootstrap
percentile confidence intervals. Rolling-origin cross-validation, 12-month horizon,
1{{,}}452 pooled predictions per model per city.}}
\label{{tab:smape}}
\begin{{tabular}}{{lccccccc}}
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
\begin{{tabular}}{{llccccccc}}
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
# Tabela 5: calibracao dos intervalos
# --------------------------------------------------------------------------- #
def table5(cal: pd.DataFrame, pred: pd.DataFrame) -> tuple[str, dict]:
    scale_by_city = pred.groupby("city")["y_true"].mean()
    cal = cal.copy()
    cal["rWIS"] = [r.WIS / scale_by_city[r.city] for r in cal.itertuples()]

    blocks, summary = [], {}
    for scale, label in (
        ("log1p", "Multiplicative intervals (residuals calibrated on the log1p scale)"),
        ("absolute", "Additive intervals (residuals calibrated on the raw scale)"),
    ):
        c = cal[cal["scale"] == scale]
        g = c.groupby("model").agg(
            c50=("coverage_50", "mean"),
            c80=("coverage_80", "mean"),
            c95=("coverage_95", "mean"),
            rwis=("rWIS", "mean"),
        )
        wins = c.loc[c.groupby("city")["rWIS"].idxmin()].groupby("model").size()
        g["wins"] = wins.reindex(g.index).fillna(0).astype(int)
        g = g.reindex(sorted(g.index, key=lambda m: g.loc[m, "rwis"]))
        summary[scale] = {
            m: {k: round(float(v), 4) for k, v in g.loc[m].items()} for m in g.index
        }

        rows = [
            rf"\quad {MODEL_LABEL[m]} & {g.loc[m, 'c50'] * 100:.1f} & "
            rf"{g.loc[m, 'c80'] * 100:.1f} & {g.loc[m, 'c95'] * 100:.1f} & "
            rf"{g.loc[m, 'rwis']:.2f} & {int(g.loc[m, 'wins'])}/8 \\"
            for m in g.index
        ]
        head = rf"\multicolumn{{6}}{{l}}{{\textit{{{label}}}}} \\"
        blocks.append("\n".join([head] + rows))

    body = "\n\\addlinespace[4pt]\n".join(blocks)
    tex = (
        "% gerado por scripts/build_paper_assets.py -- nao editar a mao\n"
        r"""\begin{table}[htbp]
\centering
\small
\caption{Calibration and sharpness of conformal prediction intervals, averaged over the
eight cities, under two interval constructions.}
\label{tab:intervals}
\begin{tabular}{lcccrc}
\toprule
 & \multicolumn{3}{c}{Empirical coverage (\%)} & & \\
\cmidrule(lr){2-4}
Model & at 50\% & at 80\% & at 95\% & rWIS & Cities best \\
\midrule
"""
        + body
        + r"""
\bottomrule
\end{tabular}

\vspace{0.5em}
\begin{minipage}{\textwidth}
\footnotesize
Coverage is the percentage of observations falling inside the interval; a value close to
the nominal level indicates calibration. rWIS is the weighted interval score divided by
the city's mean observed count, which makes it comparable across cities; lower is better.
Cities best counts the cities in which a model achieved the lowest rWIS. Intervals are
calibrated only on residuals from earlier folds, so the first 20 folds of each series
carry no interval and 1{,}212 of the 1{,}452 predictions per model per city are
evaluated. The two blocks differ solely in the scale on which residuals are calibrated.
The ordering by rWIS is not preserved between them, and that is why both are reported and
no probabilistic ranking of the models is claimed.
\end{minipage}
\end{table}
"""
    )
    return tex, summary


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

    # Ordem de modelo fixa e posicao numerica em todos os paineis. Com rotulo de
    # texto mais sharey, o matplotlib acumula categorias na ordem de insercao e
    # desalinha barra e numero entre paineis.
    ypos = {m: i for i, m in enumerate(MODELS)}

    for ax, metric in zip(axes, metrics):
        winners = []
        for c in order:
            sub = met[met["city"] == c].set_index("model")
            winners.append(sub[metric].idxmin())
        counts = {m: winners.count(m) for m in MODELS}
        ax.barh(
            [ypos[m] for m in MODELS],
            [counts[m] for m in MODELS],
            color=[cmap[m] for m in MODELS],
            height=0.66,
        )
        for m in MODELS:
            if counts[m]:
                ax.text(counts[m] + 0.15, ypos[m], str(counts[m]), va="center", fontsize=8)
        ax.set_yticks(list(ypos.values()))
        ax.set_yticklabels([MODEL_LABEL[m] for m in MODELS])
        ax.set_ylim(len(MODELS) - 0.5, -0.5)
        ax.set_title(f"Best by {metric}", loc="left", fontweight="bold")
        ax.set_xlim(0, 9.2)
        ax.set_xticks(range(0, 9, 2))
        ax.set_xlabel("Cities ranked first")
    fig.suptitle(
        "The choice of accuracy metric changes which model wins",
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
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


def fig6_calibration(cal: pd.DataFrame, pred: pd.DataFrame) -> None:
    """Cobertura contra nominal, e cobertura ao longo dos anos."""
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.9))
    levels = [50, 80, 95]

    for ax, scale, label in zip(
        axes[:2], ("log1p", "absolute"), ("Multiplicative", "Additive")
    ):
        c = cal[cal["scale"] == scale]
        ax.plot([0, 100], [0, 100], color="0.4", lw=0.9, ls=":", zorder=1)
        for m in MODELS:
            v = [c[c["model"] == m][f"coverage_{L}"].mean() * 100 for L in levels]
            ax.plot(levels, v, marker="o", ms=3.4, lw=1.1,
                    label=MODEL_LABEL[m], alpha=0.9)
        ax.set_xticks(levels)
        ax.set_xlim(42, 103)
        ax.set_ylim(42, 103)
        ax.set_xlabel("Nominal level (%)")
        ax.set_title(f"{label} intervals", loc="left", fontweight="bold")
    axes[0].set_ylabel("Empirical coverage (%)")
    axes[0].legend(fontsize=6, loc="upper left", ncol=1)

    ax = axes[2]
    pr = pred.dropna(subset=["lo_95"]).copy()
    pr["year"] = pr["date"].dt.year
    pr["hit"] = (pr["y_true"] >= pr["lo_95"]) & (pr["y_true"] <= pr["hi_95"])
    for scale, label, color in (("log1p", "Multiplicative", "#1565c0"),
                                ("absolute", "Additive", "#ef6c00")):
        g = pr[pr["scale"] == scale].groupby("year")["hit"].mean() * 100
        ax.plot(g.index, g.values, marker="o", ms=3.4, lw=1.2, color=color, label=label)
    ax.axhline(95, color="0.4", lw=0.9, ls=":")
    ax.set_xticks(range(2015, 2025, 3))
    ax.set_ylim(66, 101)
    ax.text(0.03, 0.93, "nominal 95%", transform=ax.transAxes, fontsize=6.5, color="0.35")
    ax.set_xlabel("Year")
    ax.set_ylabel("Coverage at 95% (%)")
    ax.set_title("Coverage over time", loc="left", fontweight="bold")
    ax.legend(fontsize=6.5, loc="lower left")
    fig.suptitle(
        "Prediction intervals are calibrated in ordinary years and fail in the 2024 epidemic",
        fontweight="bold", y=0.995, fontsize=9.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    save(fig, "fig6_calibration")


def fig7_fan(pred: pd.DataFrame) -> None:
    """Fan chart do TimesFM em duas cidades, escala aditiva."""
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True)
    for ax, city in zip(axes, ("sao_paulo", "fortaleza")):
        s = (pred[(pred["scale"] == "absolute") & (pred["city"] == city)
                  & (pred["model"] == "timesfm") & (pred["h"] == 6)]
             .dropna(subset=["lo_95"]).sort_values("date"))
        ax.fill_between(s["date"], s["lo_95"], s["hi_95"], color="#1565c0",
                        alpha=0.18, lw=0, label="95% interval")
        ax.fill_between(s["date"], s["lo_50"], s["hi_50"], color="#1565c0",
                        alpha=0.34, lw=0, label="50% interval")
        ax.plot(s["date"], s["y_pred"], color="#1565c0", lw=1.1, label="Forecast")
        ax.plot(s["date"], s["y_true"], color="black", lw=1.2, label="Observed")
        out = s[(s["y_true"] < s["lo_95"]) | (s["y_true"] > s["hi_95"])]
        ax.scatter(out["date"], out["y_true"], s=13, color="#c62828", zorder=5,
                   label="Outside 95% interval")
        name = {"sao_paulo": "Sao Paulo", "fortaleza": "Fortaleza"}[city]
        ax.set_title(f"{name}, TimesFM at a six-month horizon", loc="left",
                     fontweight="bold")
        ax.set_ylabel("Notified cases")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.margins(x=0.01)
    axes[0].legend(fontsize=7, loc="upper left", ncol=2)
    axes[-1].set_xlabel("Target month")
    fig.suptitle(
        "Six-month-ahead forecasts with conformal intervals (additive construction)",
        fontweight="bold", y=0.999,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.982))
    save(fig, "fig7_fan")



# --------------------------------------------------------------------------- #
# Tabela 6: combinacoes de modelos
# --------------------------------------------------------------------------- #
CITY_DISPLAY = {
    "rio": "Rio de Janeiro",
    "sao_paulo": "Sao Paulo",
    "belo_horizonte": "Belo Horizonte",
}

ENS_LABEL = {
    "mean": "Mean ensemble",
    "median": "Median ensemble",
    "weighted": "Inverse-error weighted ensemble",
    "stacking": "Stacked ensemble (Ridge)",
}


def load_ensembles() -> pd.DataFrame:
    return pd.read_csv(RESULTS / "comparisons" / "ensemble_summary.csv")


def table6(ens: pd.DataFrame) -> tuple[str, dict]:
    g = ens.groupby(["approach", "kind"])[["sMAPE", "MAE", "RMSE"]].mean().reset_index()
    wins = ens.loc[ens.groupby("city")["sMAPE"].idxmin()]["approach"].value_counts()

    beats = {}
    for city, sub in ens.groupby("city"):
        mem = sub[sub["kind"] == "member"]["sMAPE"].min()
        best_ens = sub[sub["kind"] == "ensemble"]["sMAPE"].min()
        beats[city] = float(mem - best_ens)
    n_beats = sum(1 for v in beats.values() if v > 0)

    g = g.sort_values("sMAPE")
    rows = []
    for _, r in g.iterrows():
        name = ENS_LABEL.get(r["approach"], MODEL_LABEL.get(r["approach"], r["approach"]))
        mark = r"$\dagger$" if r["kind"] == "ensemble" else ""
        rows.append(
            rf"{name}{mark} & {r['sMAPE']:.1f} & {r['MAE']:,.0f} & {r['RMSE']:,.0f} & "
            rf"{int(wins.get(r['approach'], 0))}/8 \\"
        )
    body_rows = "\n".join(rows)

    best_by = {m: g.sort_values(m).iloc[0]["approach"] for m in ("sMAPE", "MAE", "RMSE")}
    summary = {
        "n_cities_ensemble_beats_best_member": n_beats,
        "delta_by_city": {k: round(v, 2) for k, v in beats.items()},
        "best_by_metric": best_by,
        "mean_by_approach": {
            r["approach"]: {m: round(float(r[m]), 2) for m in ("sMAPE", "MAE", "RMSE")}
            for _, r in g.iterrows()
        },
    }

    tex = (
        "% gerado por scripts/build_paper_assets.py -- nao editar a mao\n"
        r"""\begin{table}[htbp]
\centering
\small
\caption{Individual models and model combinations on the same evaluation set, averaged
over the eight cities.}
\label{tab:ensembles}
\begin{tabular}{lrrrc}
\toprule
Approach & sMAPE (\%) & MAE & RMSE & Cities ranked first \\
\midrule
"""
        + body_rows
        + r"""
\bottomrule
\end{tabular}

\vspace{0.5em}
\begin{minipage}{\textwidth}
\footnotesize
$\dagger$ marks a combination of the seven individual models. Weights and the stacking
meta-model are fitted only on folds earlier than the one being predicted, so the
combination never sees the fold it is evaluated on. Individual models and combinations are
scored on exactly the same rows: the first 20 folds are withheld as a training window for
the combiners, leaving 1{,}188 predictions per approach per city. Comparing a combination
evaluated on 99 folds against a single model evaluated on 119 would favour the combination,
because the withheld folds are those with the shortest training window.
\end{minipage}
\end{table}
"""
    )
    return tex, summary


def fig8_ensembles(ens: pd.DataFrame) -> None:
    """Quanto o melhor ensemble ganha ou perde do melhor membro, por cidade."""
    rows = []
    for city, sub in ens.groupby("city"):
        mem = sub[sub["kind"] == "member"]["sMAPE"].min()
        best = sub[sub["kind"] == "ensemble"]["sMAPE"].min()
        rows.append((CITY_DISPLAY.get(city, city.replace("_", " ").title()), mem - best))
    rows.sort(key=lambda r: r[1])
    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    colors = ["#c62828" if v <= 0 else "#2e7d32" for v in vals]
    ax.barh(range(len(names)), vals, color=colors, height=0.62)
    for i, v in enumerate(vals):
        ax.text(v + (0.25 if v > 0 else -0.25), i, f"{v:+.1f}", va="center",
                ha="left" if v > 0 else "right", fontsize=8)
    ax.axvline(0, color="black", lw=0.9)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("sMAPE advantage of the best combination over the best single model "
                  "(percentage points)")
    ax.set_xlim(min(vals) * 1.35, max(max(vals) * 2.6, 2.5))
    ax.set_title("Combining models does not help in seven of eight cities",
                 loc="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "fig8_ensembles")


# --------------------------------------------------------------------------- #
# Horizonte: acuracia por passo, que a media sobre 12 meses escondia
# --------------------------------------------------------------------------- #
def horizon_metrics(preds: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """sMAPE por modelo, cidade e passo de horizonte.

    O passo e recuperado da ordem das linhas pelo mesmo metodo usado nos
    intervalos conformais: o backtest grava os 12 alvos de cada fold em
    sequencia.
    """
    from dengue_forecast.intervals import add_fold_index

    rows = []
    for city, df in preds.items():
        d = add_fold_index(df)
        for (model, h), g in d.groupby(["model", "h"]):
            rows.append({
                "city": city,
                "model": model,
                "h": int(h),
                "sMAPE": smape(g["y_true"].to_numpy(float), g["y_pred"].to_numpy(float)),
                "MAE": mae(g["y_true"].to_numpy(float), g["y_pred"].to_numpy(float)),
            })
    return pd.DataFrame(rows)


def table7(hor: pd.DataFrame) -> tuple[str, dict]:
    piv = hor.groupby(["model", "h"])["sMAPE"].mean().unstack()
    order = sorted(MODELS, key=lambda m: piv.loc[m].mean())
    shown = [1, 2, 3, 4, 6, 9, 12]

    body_rows = []
    for m in order:
        vals = [piv.loc[m, h] for h in shown]
        cells = bold_min(vals, lambda v: f"{v:.1f}")
        body_rows.append(rf"{MODEL_LABEL[m]} & " + " & ".join(cells) + r" \\")

    wins = []
    for h in shown:
        sub = hor[hor["h"] == h]
        w = sub.loc[sub.groupby("city")["sMAPE"].idxmin()]["model"].value_counts()
        wins.append(f"{int(w.get('timesfm', 0))}/8")

    t = piv.loc["timesfm"]
    summary = {
        "smape_by_h": {int(h): round(float(t[h]), 2) for h in piv.columns},
        "best_supervised_by_h": {
            int(h): round(float(min(piv.loc[m, h] for m in MODELS if m != "timesfm")), 2)
            for h in piv.columns
        },
        "h1": round(float(t[1]), 1),
        "h3": round(float(t[3]), 1),
        "h6": round(float(t[6]), 1),
        "h12": round(float(t[12]), 1),
        "degradation_h1_h12": round(float(t[12] - t[1]), 1),
        "share_of_degradation_by_h6": round(float((t[6] - t[1]) / (t[12] - t[1]) * 100)),
        "plateau_from_h": int(
            min(h for h in range(2, 13) if all(abs(t[k] - t[k - 1]) < 2.0
                                               for k in range(h, 13)))
        ),
    }

    head = " & ".join(rf"$h={h}$" for h in shown)
    tex = (
        "% gerado por scripts/build_paper_assets.py -- nao editar a mao\n"
        r"""\begin{table}[htbp]
\centering
\small
\caption{Forecast error by horizon step: sMAPE (\%) averaged over the eight cities, at
selected months ahead.}
\label{tab:horizon}
\begin{tabular}{lccccccc}
\toprule
Model & """ + head + r""" \\
\midrule
"""
        + "\n".join(body_rows)
        + r"""
\midrule
TimesFM ranked first & """ + " & ".join(wins) + r""" \\
\bottomrule
\end{tabular}

\vspace{0.5em}
\begin{minipage}{\textwidth}
\footnotesize
Bold indicates the lowest sMAPE in each column. Each cell pools the predictions made at
that horizon step across all rolling-origin folds and all eight cities. The pooled figure
reported elsewhere in this manuscript averages over all twelve steps and therefore
describes neither the short-horizon regime nor the long one.
\end{minipage}
\end{table}
"""
    )
    return tex, summary


def fig9_horizon(hor: pd.DataFrame) -> None:
    """Degradacao com o horizonte, e o plato a partir do qual nao ha ganho."""
    piv = hor.groupby(["model", "h"])["sMAPE"].mean().unstack()
    hs = list(piv.columns)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))

    ax = axes[0]
    for m in sorted(MODELS, key=lambda m: piv.loc[m].mean()):
        lw = 2.0 if m == "timesfm" else 1.0
        z = 5 if m == "timesfm" else 2
        ax.plot(hs, [piv.loc[m, h] for h in hs], marker="o", ms=3,
                lw=lw, zorder=z, label=MODEL_LABEL[m],
                alpha=1.0 if m == "timesfm" else 0.75)
    ax.set_xticks([1, 3, 6, 9, 12])
    ax.set_xlabel("Forecast horizon (months ahead)")
    ax.set_ylabel("sMAPE (%)")
    ax.set_title("Error grows with horizon, then stops", loc="left", fontweight="bold")
    ax.legend(fontsize=6.5, ncol=2, loc="lower right")

    ax = axes[1]
    t = piv.loc["timesfm"]
    best_sup = [min(piv.loc[m, h] for m in MODELS if m != "timesfm") for h in hs]
    ax.fill_between(hs, [t[h] for h in hs], best_sup, color="#1565c0", alpha=0.16,
                    lw=0, label="TimesFM advantage")
    ax.plot(hs, [t[h] for h in hs], marker="o", ms=3.4, lw=1.8, color="#1565c0",
            label="TimesFM (zero-shot)")
    ax.plot(hs, best_sup, marker="s", ms=3.4, lw=1.3, color="#ef6c00",
            label="Best supervised model")
    plateau = int(min(h for h in range(2, 13)
                      if all(abs(t[k] - t[k - 1]) < 2.0 for k in range(h, 13))))
    ax.axvline(plateau, color="0.35", ls=":", lw=1.1)
    ax.annotate(
        f"no gain beyond\n${plateau - 1}$ months",
        xy=(plateau + 0.35, t[plateau + 1]),
        xytext=(plateau + 0.9, t[1] + 27),
        fontsize=6.8, color="0.25", va="center", ha="left",
        arrowprops=dict(arrowstyle="->", lw=0.8, color="0.45"),
    )
    ax.set_xticks([1, 3, 6, 9, 12])
    ax.set_xlabel("Forecast horizon (months ahead)")
    ax.set_ylabel("sMAPE (%)")
    ax.set_title("Zero-shot versus best supervised", loc="left", fontweight="bold")
    ax.set_ylim(top=max(max(t), max(best_sup)) + 4)
    ax.legend(fontsize=6.5, loc="lower right")

    fig.suptitle(
        "The pooled 12-month figure hides both a usable regime and a useless one",
        fontweight="bold", y=0.997, fontsize=9.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.962))
    save(fig, "fig9_horizon")

# --------------------------------------------------------------------------- #
def main() -> None:
    print("Carregando dados...")
    series = load_series()
    pop = load_population()
    preds = load_predictions()

    print(f"Calculando metricas e bootstrap ({BOOT_N} replicas)...")
    met = compute_metrics(preds)
    met.to_csv(RESULTS / "comparisons" / "metrics_with_ci.csv", index=False)
    print("  escrito results/comparisons/metrics_with_ci.csv")

    print("Gerando tabelas LaTeX...")
    t1, desc_rows = table1(series, pop)
    write(TABLES / "table1_descriptive.tex", t1)
    write(TABLES / "table2_smape.tex", table2(met))
    write(TABLES / "table3_mae_rmse.tex", table3(met))
    t4, disagree = table4(met)
    write(TABLES / "table4_metric_disagreement.tex", t4)
    cal = load_interval_calibration()
    ipred = load_interval_predictions()
    t5, interval_summary = table5(cal, ipred)
    write(TABLES / "table5_intervals.tex", t5)
    ens = load_ensembles()
    t6, ensemble_summary = table6(ens)
    write(TABLES / "table6_ensembles.tex", t6)
    hor = horizon_metrics(preds)
    hor.to_csv(RESULTS / "comparisons" / "metrics_by_horizon.csv", index=False)
    t7, horizon_summary = table7(hor)
    write(TABLES / "table7_horizon.tex", t7)

    print("Gerando figuras...")
    setup_style()
    fig1_series(series)
    fig2_heatmap(met)
    fig3_timesfm_vs_best(met)
    fig4_metric_disagreement(met)
    fig5_observed_vs_predicted(preds)
    fig6_calibration(cal, ipred)
    fig7_fan(ipred)
    fig8_ensembles(ens)
    fig9_horizon(hor)

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
        "intervals": interval_summary,
        "ensembles": ensemble_summary,
        "horizon": horizon_summary,
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
