"""
Plot the single median-survivor life path, age 22 -> 85, into median_path.png.

Identical spec/pool as graph/plot_5_paths.py (see graph/paths_pool.py):
50M + Rp1M/mo, 50/50 strategy+VT to 40; 70/30 VT+SBN after, spend 6M
today's money +2%/yr. Pool seed 7. Median = median ending portfolio
among paths that survive to 85. Linear y, 2.7B reference line.

Usage (from repo root):
    python graph/plot_median_path.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths_pool import (  # noqa: E402
    build_pool, START, RETIRE, DEATH, TARGET_LINE,
)

OUT = os.path.join("graph", "median_path.png")


def main():
    pool = build_pool()
    full, ages = pool["full"], pool["ages"]
    ending, failed = pool["ending"], pool["failed"]
    print("junction OK | median landing at 40: Rp%.2fB | P(success): %.1f%%" % (
        np.median(pool["at40"]) / 1e9, 100 * (1 - np.mean(failed))))

    surv = np.where(~failed)[0]
    order = np.argsort(ending[surv])
    midx = int(surv[order[len(order) // 2]])
    path = full[midx]
    print("median survivor: sim %d at40=Rp%.2fB end=Rp%.2fB" % (
        midx, path[RETIRE - START] / 1e9, ending[midx] / 1e9))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axvspan(START, RETIRE, color="#e3f2fd", alpha=0.6)
    ax.axvspan(RETIRE, DEATH, color="#fff3e0", alpha=0.6)
    ax.plot(ages, path, color="#1e88e5", lw=2.6,
            label="Median survivor (sim %d)" % midx)
    ax.axhline(TARGET_LINE, color="#43a047", ls="--", lw=1.6,
               label="Target Rp2.7B at 40 (reference)")
    ax.axvline(RETIRE, color="black", ls=":", lw=1.4)
    # annotations: landing at 40, ending at 85
    ax.scatter([RETIRE], [path[RETIRE - START]], color="#1e88e5", s=70, zorder=5)
    ax.annotate("40: Rp%.2fB" % (path[RETIRE - START] / 1e9),
                xy=(RETIRE, path[RETIRE - START]),
                xytext=(RETIRE - 9, path[RETIRE - START] * 1.35),
                fontsize=10, color="#0d47a1",
                arrowprops=dict(arrowstyle="->", color="#0d47a1"))
    ax.scatter([DEATH], [ending[midx]], color="#1e88e5", s=70, zorder=5)
    ax.annotate("85: Rp%.2fB" % (ending[midx] / 1e9),
                xy=(DEATH, ending[midx]),
                xytext=(DEATH - 12, ending[midx] * 0.82),
                fontsize=10, color="#0d47a1",
                arrowprops=dict(arrowstyle="->", color="#0d47a1"))
    ax.text(30, 0.02, "22–40: 50% Strategy / 50% VT · save Rp1M/mo",
            transform=ax.get_xaxis_transform(), ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#90caf9"))
    ax.text(63, 0.02, "41–85: 70% VT / 30% SBN · spend 6M→8.57M +2%/yr",
            transform=ax.get_xaxis_transform(), ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#ffcc80"))
    ax.set_xlim(START, DEATH)
    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio (IDR)")
    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda v, _: "Rp%.0fB" % (v / 1e9) if v >= 1e9 else "Rp%.0fM" % (v / 1e6)))
    ax.set_title("Median life path: save Rp1M/mo to 40, then spend 6M/mo (Block Bootstrap DMS, seed 7)")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
