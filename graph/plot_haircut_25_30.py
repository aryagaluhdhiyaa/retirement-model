"""
Honest-set mirrors: same life paths under haircut accumulation legs.

Two variants, one per strategy-leg CAGR (rescaled joint blocks — crash
structure preserved, stock leg untouched at 11.24% bull-window):
  25% -> data/history_joint_25pct.csv  (orange)
  30% -> data/history_joint_30pct.csv  (blue)
Retirement leg identical (70/30 VT+SBN, 6M spend, same draw stream), so only
the age-40 landing differs. Same pool seeds as the optimistic set.

Outputs (graph/ folder):
  median_haircut_25_30.png — median@25 + median@30, landing/ending callouts
  p25_haircut_25_30.png    — P25@25 + P25@30, landing/ending callouts
  paths5_haircut_25_30.png — same two medians, head-to-head framing
                             (phase shading, ending-value legend, no arrows)

Usage (from repo root):
    python graph/plot_haircut_25_30.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths_pool import (  # noqa: E402
    build_pool, N_SIMS, START, RETIRE, DEATH, TARGET_LINE,
)

VARIANTS = [
    ("25%", "data/history_joint_25pct.csv", "#ef6c00"),
    ("30%", "data/history_joint_30pct.csv", "#1e88e5"),
]

PHASE_A = "22–40: 50% Strategy / 50% VT · save Rp1M/mo"
PHASE_B = "41–85: 70% VT / 30% SBN · spend 6M→8.57M +2%/yr"


def pick_median(pool):
    surv = np.where(~pool["failed"])[0]
    order = np.argsort(pool["ending"][surv])
    return int(surv[order[len(order) // 2]])


def pick_p25(pool):
    return int(np.argsort(pool["ending"])[N_SIMS // 4])


def base_fig(title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axvspan(START, RETIRE, color="#e3f2fd", alpha=0.6)
    ax.axvspan(RETIRE, DEATH, color="#fff3e0", alpha=0.6)
    ax.axhline(TARGET_LINE, color="#43a047", ls="--", lw=1.6,
               label="Target Rp2.7B at 40 (reference)")
    ax.axvline(RETIRE, color="black", ls=":", lw=1.4)
    ax.text(30, 0.02, PHASE_A, transform=ax.get_xaxis_transform(),
            ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#90caf9"))
    ax.text(63, 0.02, PHASE_B, transform=ax.get_xaxis_transform(),
            ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#ffcc80"))
    ax.set_xlim(START, DEATH)
    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio (IDR)")
    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda v, _: "Rp%.0fB" % (v / 1e9) if v >= 1e9 else "Rp%.0fM" % (v / 1e6)))
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    return fig, ax


def annotate(ax, ages, path, color, dark):
    ax.scatter([RETIRE], [path[RETIRE - START]], color=color, s=70, zorder=5)
    ax.annotate("40: Rp%.2fB" % (path[RETIRE - START] / 1e9),
                xy=(RETIRE, path[RETIRE - START]),
                xytext=(RETIRE - 11, path[RETIRE - START] * 1.5 + 1e9),
                fontsize=10, color=dark,
                arrowprops=dict(arrowstyle="->", color=dark))
    ax.scatter([DEATH], [path[-1]], color=color, s=70, zorder=5)
    ax.annotate("85: Rp%.2fB" % (path[-1] / 1e9),
                xy=(DEATH, path[-1]),
                xytext=(DEATH - 14, path[-1] * 0.80 + 1e9),
                fontsize=10, color=dark,
                arrowprops=dict(arrowstyle="->", color=dark))


def main():
    pools = {}
    for tag, path, _ in VARIANTS:
        pools[tag] = build_pool(joint_path=path)
        p = pools[tag]
        print("%s pool: median landing Rp%.2fB | P(success) %.1f%%" % (
            tag, np.median(p["at40"]) / 1e9, 100 * (1 - np.mean(p["failed"]))))

    # ── 1. medians head-to-head (annotated) ──────────────────────────────
    fig, ax = base_fig("Median life path under haircut strategy: 25% vs 30% (Block Bootstrap DMS, seed 7)")
    for tag, _, color in VARIANTS:
        p = pools[tag]
        midx = pick_median(p)
        dark = "#e65100" if tag == "25%" else "#0d47a1"
        ax.plot(p["ages"], p["full"][midx], color=color, lw=2.6,
                label="Median @%s strategy (sim %d)" % (tag, midx))
        annotate(ax, p["ages"], p["full"][midx], color, dark)
        print("median@%s: sim %d at40=Rp%.2fB end=Rp%.2fB" % (
            tag, midx, p["full"][midx, RETIRE - START] / 1e9, p["ending"][midx] / 1e9))
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join("graph", "median_haircut_25_30.png"), dpi=300)
    print("wrote median_haircut_25_30.png")

    # ── 2. P25 head-to-head (annotated) ──────────────────────────────────
    fig, ax = base_fig("25th-percentile life path under haircut strategy: 25% vs 30% (Block Bootstrap DMS, seed 7)")
    for tag, _, color in VARIANTS:
        p = pools[tag]
        q = pick_p25(p)
        dark = "#e65100" if tag == "25%" else "#0d47a1"
        is_fail = bool(p["failed"][q])
        ax.plot(p["ages"], p["full"][q], color=color, lw=2.6,
                label="P25 @%s strategy (sim %d%s)" % (tag, q, ", FAILED" if is_fail else ""))
        annotate(ax, p["ages"], p["full"][q], color, dark)
        print("P25@%s: sim %d fail=%s at40=Rp%.2fB end=Rp%.2fB" % (
            tag, q, is_fail, p["full"][q, RETIRE - START] / 1e9, p["ending"][q] / 1e9))
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join("graph", "p25_haircut_25_30.png"), dpi=300)
    print("wrote p25_haircut_25_30.png")

    # ── 3. paths5-style comparison framing (same two medians, no arrows) ──
    fig, ax = base_fig("Head-to-head: median life at 25% vs 30% strategy (save Rp1M/mo, spend 6M/mo)")
    for tag, _, color in VARIANTS:
        p = pools[tag]
        midx = pick_median(p)
        ax.plot(p["ages"], p["full"][midx], color=color, lw=2.4,
                label="Median @%s: 40=Rp%.2fB → 85=Rp%.2fB" % (
                    tag, p["full"][midx, RETIRE - START] / 1e9, p["ending"][midx] / 1e9))
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join("graph", "paths5_haircut_25_30.png"), dpi=300)
    print("wrote paths5_haircut_25_30.png")


if __name__ == "__main__":
    main()
