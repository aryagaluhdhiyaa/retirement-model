"""
Shared 22->85 life-path pool for the path-plot scripts.

Phase 1 (22-40): 50M initial + Rp1M/mo, 50% My Strategy / 50% VT(=ACWI),
                 joint history file, nothing withdrawn.
Phase 2 (41-85): 70% VT / 30% SBN bonds, spend 6M today's money inflated
                 2%/yr (8.57M/mo at 40), DMS market file (7.2% + 6% SBN).
Engine: Block Bootstrap, 6-month joint blocks. Pool seed 7 (20k sims),
retirement draw stream seed 7001.
Decumulation replicates run_simulation conventions exactly:
beginning-of-year withdrawal, clamp at 0, failure = cannot fund withdrawal.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import run_accumulation_simulation  # noqa: E402
from bootstrap import load_history, sample_annual_returns  # noqa: E402

POOL_SEED = 7
RETIRE_STREAM_SEED = 7001
N_SIMS = 20_000
INIT, MONTHLY = 50_000_000, 1_000_000
START, RETIRE, DEATH = 22, 40, 85
INFL = 0.02
SPEND_TODAY = 6_000_000
ACC_ALLOC = 0.50
RET_ALLOC = 0.70
TARGET_LINE = 2_700_000_000


JOINT_DEFAULT = "data/history_joint_stock_strategy.csv"


def build_pool(joint_path=JOINT_DEFAULT):
    """Returns dict with full, ages, ending, failed, fail_age, at40, spend40.

    joint_path selects the accumulation-leg history (default: 39.2% corrected
    joint file; haircut variants: history_joint_25pct/30pct.csv). The
    retirement leg is always the DMS market file and always uses the same
    draw stream, so only the age-40 landing differs across variants.
    """
    acc = run_accumulation_simulation(
        initial_portfolio=INIT, monthly_contribution=MONTHLY,
        stock_allocation=ACC_ALLOC,
        stock_return=0.072, stock_std=0.17,
        bond_return=0.40, bond_std=0.23,
        current_age=START, retirement_age=RETIRE,
        num_simulations=N_SIMS, seed=POOL_SEED,
        return_model="bootstrap", bootstrap_block_months=6,
        bootstrap_history_path=joint_path,
    )
    acc_paths = acc["portfolio_paths"]
    at40 = acc_paths[:, -1].copy()

    n_years = DEATH - RETIRE
    spend40 = SPEND_TODAY * (1 + INFL) ** (RETIRE - START)
    sched = np.array([spend40 * 12 * (1 + INFL) ** t for t in range(n_years)])

    rng = np.random.default_rng(RETIRE_STREAM_SEED)
    hist = load_history("data/history_market.csv")
    s_ret, b_ret = sample_annual_returns(
        rng, N_SIMS, n_years, block_months=6, history=hist,
        stock_return=0.072, stock_std=0.17, bond_return=0.06, bond_std=0.115)
    port_ret = RET_ALLOC * s_ret + (1 - RET_ALLOC) * b_ret

    ret_paths = np.zeros((N_SIMS, n_years + 1))
    ret_paths[:, 0] = at40
    failed = np.zeros(N_SIMS, dtype=bool)
    fail_age = np.full(N_SIMS, -1)
    for t in range(n_years):
        after_wd = ret_paths[:, t] - sched[t]
        newly_failed = (after_wd <= 0) & (~failed)
        failed |= newly_failed
        fail_age[newly_failed] = RETIRE + t
        after_wd = np.maximum(after_wd, 0.0)
        ret_paths[:, t + 1] = np.maximum(after_wd * (1 + port_ret[:, t]), 0.0)

    full = np.concatenate([acc_paths, ret_paths[:, 1:]], axis=1)
    ages = np.arange(START, DEATH + 1)
    assert full.shape == (N_SIMS, len(ages))
    assert np.allclose(full[:, RETIRE - START], at40), "junction broken"
    return {"full": full, "ages": ages, "ending": full[:, -1],
            "failed": failed, "fail_age": fail_age, "at40": at40,
            "spend40": spend40}
