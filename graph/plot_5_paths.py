"""
Plot 5 curated life paths, age 22 -> 85, into 5_random_path.png.

Shared pool/spec in graph/paths_pool.py (identical engines, seeds, funding:
50M + Rp1M/mo, 50/50 strategy+VT to 40; 70/30 VT+SBN after, spend 6M
today's money +2%/yr; pool seed 7, retire stream 7001).
Curated 5: median + 2 random survivors (blue), 2 random failures
(red, clamped flat at 0). Curation sub-seed 777.
No pin: paths land where they land; 2.7B is a reference line only.

Usage (from repo root):
    python graph/plot_5_paths.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths_pool import (  # noqa: E402
    build_pool, START, RETIRE, DEATH, TARGET_LINE,
)

CURATE_SEED = 777
OUT = os.path.join("graph", "5_random_path.png")


def main():
    pool = build_pool()
    full, ages = pool["full"], pool["ages"]
    ending, failed = pool["ending"], pool["failed"]
    fail_age = pool["fail_age"]
    print("junction OK (age-40 continuous) | median landing at 40: Rp%.2fB | "
          "P(success to 85): %.1f%%" % (
              np.median(pool["at40"]) / 1e9, 100 * (1 - np.mean(failed))))

    surv = np.where(~failed)[0]
    fail = np.where(failed)[0]
    order = np.argsort(ending[surv])
    median_idx = int(surv[order[len(order) // 2]])
    sub = np.random.default_rng(CURATE_SEED)
    others = [i for i in surv if i != median_idx]
    extra_surv = sub.choice(others, size=min(2, len(others)), replace=False).tolist()
    picks_surv = [median_idx] + extra_surv
    if len(fail) >= 2:
        picks_fail = sub.choice(fail, size=2, replace=False).tolist()
    else:  # guard: not enough failures — take worst survivors (shouldn't happen)
        picks_fail = [int(surv[order[k]]) for k in range(min(2, len(order)))]
        print("WARNING: fewer than 2 failures in pool; using worst survivors")
    picks = [(i, False) for i in picks_surv] + [(i, True) for i in picks_fail]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.axvspan(START, RETIRE, color="#e3f2fd", alpha=0.6)
    ax.axvspan(RETIRE, DEATH, color="#fff3e0", alpha=0.6)
    for idx, is_fail in picks:
        if not is_fail:
            label = "Survivor (sim %d) — ends Rp%.2fB" % (idx, ending[idx] / 1e9)
            lw = 2.6 if idx == median_idx else 1.8
            if idx == median_idx:
                label = "MEDIAN " + label
            ax.plot(ages, full[idx], color="#1e88e5", lw=lw, alpha=0.9, label=label)
        else:
            fa = int(fail_age[idx])
            label = "Failed (sim %d) — broke at %d, ends Rp%.2fB" % (idx, fa, ending[idx] / 1e9)
            ax.plot(ages, full[idx], color="#e53935", lw=2.0, alpha=0.9, label=label)
            ax.scatter([fa], [0], color="#e53935", s=60, zorder=5)
    ax.axhline(TARGET_LINE, color="#43a047", ls="--", lw=1.6, label="Target Rp2.7B at 40 (reference)")
    ax.axvline(RETIRE, color="black", ls=":", lw=1.4)
    ax.text(30, 0.02, "22–40: 50% Strategy / 50% VT · save Rp1M/mo",
            transform=ax.get_xaxis_transform(), ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#90caf9"))
    ax.text(63, 0.02, "41–85: 70% VT / 30% SBN · spend 6M→8.57M +2%/yr",
            transform=ax.get_xaxis_transform(), ha="center", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="#ffcc80"))
    ax.set_xlim(START, DEATH)
    ax.set_xlabel("Age")
    ax.set_ylabel("Portfolio (IDR)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: "Rp%.0fB" % (v / 1e9) if v >= 1e9 else "Rp%.0fM" % (v / 1e6)))
    ax.set_title("5 life paths: save Rp1M/mo to 40, then spend 6M/mo (Block Bootstrap DMS, seed 7)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT, dpi=300)
    print("wrote", OUT)
    for idx, is_fail in picks:
        print("sim %d fail=%s at40=Rp%.2fB end=Rp%.2fB fail_age=%s" % (
            idx, is_fail, full[idx, RETIRE - START] / 1e9, ending[idx] / 1e9,
            int(fail_age[idx]) if is_fail else "-"))


if __name__ == "__main__":
    main()
