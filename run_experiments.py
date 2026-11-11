"""
Experimenten met het silo-model
===============================

Draai dit script om alle resultaten en grafieken opnieuw te maken:

    python run_experiments.py           # volledige versie (paar minuten)
    python run_experiments.py --quick   # snelle versie om te testen

Alles komt in de map results/.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from silo_model import ENGINEER, MANAGER, final_values, run_many, run_model

RESULTS = Path(__file__).parent / "results"

# --- huisstijl voor de grafieken -----------------------------------------
BLUE = "#2a78d6"      # engineers / hoofdreeks
ORANGE = "#eb6834"    # managers
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "font.size": 10,
    "legend.frameon": False,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
})

# --- de interventies die we vergelijken ----------------------------------
SCENARIOS = {
    "Basis": {},
    "Gedeeld projectdoel": dict(shared_goal=0.05),
    "Plat organiseren": dict(status_gap=0.1),
    "Training werktaal": dict(language_gap=0.3),
    "Brugfiguren (9)": dict(n_bridges=9),
    "Meer projectcontact": dict(forced_contact=0.4),
}
SCENARIOS["Alles samen"] = {k: v for d in SCENARIOS.values() for k, v in d.items()}


def add_trust_columns(data):
    data["Vertrouwen (gemiddeld)"] = (
        data["Vertrouwen engineers"] * 45 + data["Vertrouwen managers"] * 15
    ) / 60
    return data


def band(ax, data, column, colour, label=None):
    """Mediaan over runs met een band van het 10e tot 90e percentiel."""
    g = data.groupby("tick")[column]
    mid, lo, hi = g.median(), g.quantile(0.1), g.quantile(0.9)
    ax.fill_between(mid.index, lo, hi, color=colour, alpha=0.15, linewidth=0)
    ax.plot(mid.index, mid, color=colour, linewidth=2, label=label)
    return mid


# --------------------------------------------------------------------------
# 1. Basisrun: ontstaan er silo's zonder ingrijpen?
# --------------------------------------------------------------------------
def experiment_basisrun(runs, steps):
    data = add_trust_columns(run_many(runs=runs, steps=steps))
    data.to_csv(RESULTS / "01_basisrun.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharex=True)
    _, model = run_model(steps=1, seed=0)

    ax = axes[0]
    mid = band(ax, data, "E-I index", BLUE)
    ax.axhline(model.ei_random, color=MUTED, linestyle="--", linewidth=1)
    ax.text(steps, model.ei_random + 0.01, "willekeurige partnerkeuze",
            color=INK_2, fontsize=9, ha="right", va="bottom")
    ax.set_title("Silo-index (E-I) daalt")
    ax.set_ylabel("E-I index  (−1 = volledig silo)")

    ax = axes[1]
    band(ax, data, "Vertrouwen (gemiddeld)", BLUE)
    ax.set_title("Vertrouwen in de andere groep daalt")
    ax.set_ylabel("vertrouwen (0–1)")
    ax.set_ylim(0, 1)

    ax = axes[2]
    e = band(ax, data, "Identificatie engineers", BLUE, "engineers")
    m = band(ax, data, "Identificatie managers", ORANGE, "managers")
    ax.text(steps, e.iloc[-1] + 0.03, "engineers", color=INK_2, ha="right", fontsize=9)
    ax.text(steps, m.iloc[-1] - 0.06, "managers", color=INK_2, ha="right", fontsize=9)
    ax.legend(loc="lower left")
    ax.set_title("Engineers voelen zich meer 'kamp'")
    ax.set_ylabel("groepsidentificatie (0–1)")
    ax.set_ylim(0, 1)

    for ax in axes:
        ax.set_xlabel("tick (werkdag)")
    fig.suptitle(f"Basisrun zonder interventies — mediaan en 10–90% van {runs} runs",
                 x=0.01, ha="left", color=INK_2, fontsize=10, y=1.02)
    fig.savefig(RESULTS / "01_basisrun.png")
    plt.close(fig)

    end = data[data["tick"] == steps]
    return {
        "E-I index eerste 10 dagen": data[data["tick"] <= 10]["E-I index"].median(),
        "E-I index eind": end["E-I index"].median(),
        "E-I bij willekeurig contact": model.ei_random,
        "Vertrouwen eind": end["Vertrouwen (gemiddeld)"].median(),
        "Identificatie engineers eind": end["Identificatie engineers"].median(),
    }


# --------------------------------------------------------------------------
# 2. Netwerk: hoe ziet het informele netwerk eruit na een jaar?
# --------------------------------------------------------------------------
def draw_network(ax, model, title):
    w = model.ties
    threshold = np.quantile(w[w > 0], 0.80)  # alleen de sterkste 20% banden
    G = nx.Graph()
    for p in model.people:
        G.add_node(p.index, group=p.group, bridge=p.is_bridge)
    rows, cols = np.where(np.triu(w) >= threshold)
    for i, j in zip(rows, cols):
        G.add_edge(i, j, weight=w[i, j])
    pos = nx.spring_layout(G, weight="weight", seed=3, iterations=200)

    nx.draw_networkx_edges(G, pos, ax=ax, edge_color=AXIS, width=0.6, alpha=0.7)
    for group, colour, label in ((ENGINEER, BLUE, "engineer"), (MANAGER, ORANGE, "manager")):
        normal = [n for n, d in G.nodes(data=True) if d["group"] == group and not d["bridge"]]
        nx.draw_networkx_nodes(G, pos, nodelist=normal, ax=ax, node_color=colour,
                               node_size=55, edgecolors=SURFACE, linewidths=1, label=label)
    bridges = [n for n, d in G.nodes(data=True) if d["bridge"]]
    if bridges:
        nx.draw_networkx_nodes(G, pos, nodelist=bridges, ax=ax, node_color=SURFACE,
                               node_shape="D", node_size=55, edgecolors=BLUE,
                               linewidths=1.6, label="brugfiguur")
    ax.set_title(f"{title}\nE-I index {model.ei_index():.2f}")
    ax.legend(loc="lower left", fontsize=9)
    ax.axis("off")


def experiment_netwerk(steps):
    _, basis = run_model(steps=steps, seed=1)
    _, samen = run_model(steps=steps, seed=1, **SCENARIOS["Alles samen"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    draw_network(axes[0], basis, "Basis: managers vormen een eigen kern")
    draw_network(axes[1], samen, "Alle interventies samen: gemengd netwerk")
    fig.suptitle(f"Informeel netwerk na {steps} werkdagen (sterkste 20% van de banden)",
                 x=0.01, ha="left", color=INK_2, fontsize=10, y=1.03)
    fig.savefig(RESULTS / "02_netwerk.png")
    plt.close(fig)


# --------------------------------------------------------------------------
# 3. Interventies vergelijken
# --------------------------------------------------------------------------
def experiment_interventies(runs, steps):
    rows = []
    for name, params in SCENARIOS.items():
        data = add_trust_columns(run_many(runs=runs, steps=steps, **params))
        fv = final_values(data)
        fv["scenario"] = name
        rows.append(fv)
    per_run = pd.concat(rows).reset_index()
    per_run.to_csv(RESULTS / "03_interventies_per_run.csv", index=False)

    summary = per_run.groupby("scenario").agg(
        vertrouwen=("Vertrouwen (gemiddeld)", "mean"),
        vertrouwen_p10=("Vertrouwen (gemiddeld)", lambda x: x.quantile(0.1)),
        vertrouwen_p90=("Vertrouwen (gemiddeld)", lambda x: x.quantile(0.9)),
        ei=("E-I index", "mean"),
        ei_p10=("E-I index", lambda x: x.quantile(0.1)),
        ei_p90=("E-I index", lambda x: x.quantile(0.9)),
        identificatie_engineers=("Identificatie engineers", "mean"),
        slaagkans=("Slaagkans contact tussen groepen", "mean"),
    ).sort_values("vertrouwen")
    summary.round(3).to_csv(RESULTS / "03_interventies_samenvatting.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    y = np.arange(len(summary))
    colours = [MUTED if s == "Basis" else BLUE for s in summary.index]
    for ax, col, title, xlabel in (
        (axes[0], "vertrouwen", "Vertrouwen in de andere groep", "vertrouwen (0–1)"),
        (axes[1], "ei", "Silo-index (E-I)", "E-I index  (hoger = minder silo)"),
    ):
        vals = summary[col]
        err = [vals - summary[f"{col}_p10"], summary[f"{col}_p90"] - vals]
        ax.barh(y, vals, color=colours, height=0.6, xerr=err,
                error_kw=dict(ecolor=INK_2, elinewidth=1, capsize=2))
        for yi, v in zip(y, vals):
            ax.text(summary[f"{col}_p90"].iloc[yi] + 0.02 if v >= 0 else 0.02, yi,
                    f"{v:.2f}", va="center", fontsize=9, color=INK)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.grid(axis="y", visible=False)
        ax.axvline(0, color=AXIS, linewidth=1)
    axes[0].set_yticks(y, summary.index, color=INK)
    axes[0].set_xlim(0, 1)
    fig.suptitle(f"Interventies na {steps} werkdagen — gemiddelde en 10–90% van {runs} runs "
                 "(grijs = basis)", x=0.01, ha="left", color=INK_2, fontsize=10, y=1.02)
    fig.savefig(RESULTS / "03_interventies.png")
    plt.close(fig)
    return summary


# --------------------------------------------------------------------------
# 4. Kantelpunt: bij welke slaagkans en negativiteitsbias kantelt vertrouwen?
# --------------------------------------------------------------------------
def experiment_kantelpunt(runs, steps):
    successes = np.round(np.arange(0.50, 0.901, 0.05), 2)
    biases = np.round(np.arange(1.0, 3.01, 0.25), 2)
    rows = []
    for s in successes:
        for b in biases:
            data = add_trust_columns(
                run_many(runs=runs, steps=steps, base_success=s, negativity_bias=b)
            )
            fv = final_values(data)
            rows.append(dict(base_success=s, negativity_bias=b,
                             vertrouwen=fv["Vertrouwen (gemiddeld)"].mean(),
                             ei=fv["E-I index"].mean()))
    grid = pd.DataFrame(rows)
    grid.round(3).to_csv(RESULTS / "04_kantelpunt.csv", index=False)

    table = grid.pivot(index="negativity_bias", columns="base_success", values="vertrouwen")
    fig, ax = plt.subplots(figsize=(7.5, 5))
    im = ax.imshow(table.values, origin="lower", cmap="Blues", vmin=0, vmax=1,
                   aspect="auto", extent=[successes[0] - 0.025, successes[-1] + 0.025,
                                          biases[0] - 0.125, biases[-1] + 0.125])
    cs = ax.contour(table.columns, table.index, table.values, levels=[0.5],
                    colors=INK, linewidths=1.5)
    ax.clabel(cs, fmt="vertrouwen 0,5", fontsize=9)
    ax.plot(0.7, 2.0, marker="o", markersize=9, markerfacecolor=SURFACE,
            markeredgecolor=INK, markeredgewidth=1.5)
    ax.annotate("standaardwaarden", (0.7, 2.0), xytext=(8, 8),
                textcoords="offset points", fontsize=9, color=INK)
    ax.grid(False)
    ax.set_xlabel("basiskans dat contact met de andere groep slaagt")
    ax.set_ylabel("negativiteitsbias (slechte ervaring telt ×)")
    ax.set_title("Kleine verschillen in contactkwaliteit kantelen het vertrouwen")
    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("vertrouwen na een jaar (0–1)", color=INK_2)
    cbar.outline.set_visible(False)
    fig.savefig(RESULTS / "04_kantelpunt.png")
    plt.close(fig)
    return grid


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="minder runs (snelle test)")
    parser.add_argument("--steps", type=int, default=250, help="aantal ticks per run")
    args = parser.parse_args()

    runs = 5 if args.quick else 20
    grid_runs = 2 if args.quick else 5
    RESULTS.mkdir(exist_ok=True)

    print("1/4 Basisrun ...")
    basis = experiment_basisrun(runs, args.steps)
    for k, v in basis.items():
        print(f"    {k:32s} {v:6.3f}")

    print("2/4 Netwerk ...")
    experiment_netwerk(args.steps)

    print("3/4 Interventies ...")
    summary = experiment_interventies(runs, args.steps)
    print(summary[["vertrouwen", "ei", "identificatie_engineers", "slaagkans"]]
          .round(3).to_string())

    print("4/4 Kantelpunt ...")
    experiment_kantelpunt(grid_runs, args.steps)

    print(f"\nKlaar. Grafieken en CSV-bestanden staan in {RESULTS}/")


if __name__ == "__main__":
    main()
