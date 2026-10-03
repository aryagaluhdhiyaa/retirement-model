"""
Block bootstrap for *real market* returns (IS block bootstrap — not plain i.i.d.).

Default history (canonical engine): data/history_market.csv
  Columns: date, stock_ret, bond_ret  (monthly, joint)
  - stock_ret = International Stocks (DMS Global 7.2% nominal anchor)
  - bond_ret  = Indonesian SBN (6.0% nominal anchor, realized XISB.JK/EMB vol;
                BI Rate is a policy-rate level, not a return series, so the
                long-run leg is synthetic — see tools/fetch_study_history.py)
  When this file is missing, the engine falls back to Normal (no silent substitution).

Strategy history (e.g. data/history_strategy.csv, regenerated locally via
  tools/export_history.py — not stored in git): ONLY used when the caller
  explicitly passes its path — not by default.

Method: circular overlapping monthly BLOCKS (block_months=3/6/12), sampled with
        replacement jointly (same start index for both sleeves preserves
        cross-asset crash correlation). Monthly blocks annualized:
        r_annual = prod(1+r_month[0:12])-1 per year.
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

_HISTORY_CACHE: dict[str, pd.DataFrame] = {}

def load_history(path: str | None = None) -> pd.DataFrame | None:
    # Default is market history, NOT strategy history
    if path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        cand = os.path.join(base, "data", "history_market.csv")
        if os.path.exists(cand):
            path = cand
        else:
            return None
    if path in _HISTORY_CACHE:
        return _HISTORY_CACHE[path]
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        return None
    _HISTORY_CACHE[path] = df
    return df

def load_strategy_history(path: str | None = None) -> pd.DataFrame | None:
    if path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "data", "history_strategy.csv")
    if path in _HISTORY_CACHE:
        return _HISTORY_CACHE[path]
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    _HISTORY_CACHE[path] = df
    return df

def has_col(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns and df[col].notna().sum() >= 24

def sample_annual_returns(
    rng: np.random.Generator,
    n_sims: int,
    n_years: int,
    block_months: int = 6,
    history: pd.DataFrame | None = None,
    history_path: str | None = None,
    stock_return: float = 0.07,
    stock_std: float = 0.14,
    bond_return: float = 0.06,
    bond_std: float = 0.09,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (stock_annual, bond_annual) each shape (n_sims, n_years).
    - If market history (stock_ret + bond_ret) present: joint block bootstrap (realistic).
    - Otherwise: parametric Normal fallback (safe — no mixing with 25% strategy).
    Pass history=load_strategy_history() explicitly only when you intend to price the factor strategy.
    """
    if n_years == 0:
        return np.zeros((n_sims, 0)), np.zeros((n_sims, 0))

    if history is None:
        history = load_history(history_path)

    # No market history => parametric fallback (do NOT silently use strategy 25% history)
    if history is None or len(history) < block_months:
        stock = rng.normal(stock_return, stock_std, size=(n_sims, n_years))
        bond = rng.normal(bond_return, bond_std, size=(n_sims, n_years))
        return stock, bond

    # Strategy file mistakenly passed? It has strategy_ret not bond_ret — still handle but warn via caller
    if "strategy_ret" in history.columns and "bond_ret" not in history.columns:
        strat_m = history["strategy_ret"].to_numpy(dtype=float)
        n_obs = len(strat_m)
        total_months = n_years * 12
        strat_monthly = _block_sample_monthly(rng, strat_m, n_sims, total_months, block_months, n_obs)
        strat_annual = _annualize(strat_monthly, n_sims, n_years)
        stock_annual = rng.normal(stock_return, stock_std, size=(n_sims, n_years))
        return stock_annual, strat_annual

    has_stock = has_col(history, "stock_ret")
    has_bond = has_col(history, "bond_ret")
    if not (has_stock and has_bond):
        # partial history => parametric fallback
        stock = rng.normal(stock_return, stock_std, size=(n_sims, n_years))
        bond = rng.normal(bond_return, bond_std, size=(n_sims, n_years))
        return stock, bond

    stock_m = history["stock_ret"].to_numpy(dtype=float)
    bond_m = history["bond_ret"].to_numpy(dtype=float)
    n_obs = len(history)
    return _joint_annual_from_monthly(rng, stock_m, bond_m, n_sims, n_years, block_months, n_obs)

def _block_sample_monthly(rng, series, n_sims, total_months, block_months, n_obs):
    n_blocks = int(np.ceil(total_months / block_months))
    starts = rng.integers(0, n_obs, size=(n_sims, n_blocks))
    out = np.empty((n_sims, total_months), dtype=float)
    for b in range(n_blocks):
        s = starts[:, b]
        for k in range(block_months):
            col = b * block_months + k
            if col >= total_months:
                break
            idx = (s + k) % n_obs
            out[:, col] = series[idx]
    return out

def _joint_annual_from_monthly(rng, stock_m, bond_m, n_sims, n_years, block_months, n_obs):
    total_months = n_years * 12
    n_blocks = int(np.ceil(total_months / block_months))
    starts = rng.integers(0, n_obs, size=(n_sims, n_blocks))
    stock_monthly = np.empty((n_sims, total_months), dtype=float)
    bond_monthly = np.empty((n_sims, total_months), dtype=float)
    for b in range(n_blocks):
        s = starts[:, b]
        for k in range(block_months):
            col = b * block_months + k
            if col >= total_months:
                break
            idx = (s + k) % n_obs
            stock_monthly[:, col] = stock_m[idx]
            bond_monthly[:, col] = bond_m[idx]
    return _annualize(stock_monthly, n_sims, n_years), _annualize(bond_monthly, n_sims, n_years)

def _annualize(monthly: np.ndarray, n_sims: int, n_years: int) -> np.ndarray:
    reshaped = monthly.reshape(n_sims, n_years, 12)
    return np.prod(1.0 + reshaped, axis=2) - 1.0
