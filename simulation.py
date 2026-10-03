"""
Monte Carlo Retirement Simulation Engine

Methodology:
- Annual rebalancing to target allocation
- Beginning-of-year withdrawal (more conservative convention)
- Return model: Historical Block Bootstrap (canonical — empirical, monthly joint blocks) or Normal (missing-file fallback, i.i.d.)
- Spending increases annually by inflation
- Failure defined as portfolio <= 0 at any point during retirement horizon
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field

try:
    from bootstrap import load_history, sample_annual_returns
    _HAS_BOOTSTRAP = True
except ImportError:
    _HAS_BOOTSTRAP = False
    load_history = None  # type: ignore
    sample_annual_returns = None  # type: ignore


@dataclass
class SimulationInputs:
    """All inputs required for the Monte Carlo simulation."""
    initial_portfolio: float          # IDR
    monthly_spending: float           # IDR
    inflation: float                  # decimal (e.g., 0.03 for 3%)
    stock_allocation: float           # decimal (e.g., 0.60 for 60%)
    stock_return: float               # decimal (e.g., 0.07 for 7%)
    stock_std: float                  # decimal (e.g., 0.14 for 14%)
    bond_return: float                # decimal (e.g., 0.06 for 6%)
    bond_std: float                   # decimal (e.g., 0.09 for 9%)
    retirement_age: int
    death_age: int
    num_simulations: int
    seed: int
    # Block Bootstrap is the canonical engine ("normal" = missing-file fallback only)
    return_model: str = "bootstrap"           # "bootstrap" | "normal"
    bootstrap_block_months: int = 6           # 3,6,12 when return_model=="bootstrap"
    bootstrap_history_path: str | None = None # override path to history_monthly.csv


@dataclass
class SimulationResults:
    """Results from the Monte Carlo simulation."""
    # Portfolio paths: (num_simulations, num_years)
    portfolio_paths: np.ndarray
    # Failed simulation mask
    failed: np.ndarray               # bool array (num_simulations,)
    # Age axis for paths
    ages: np.ndarray                 # (num_years,)
    # Spending schedule
    annual_spending_schedule: np.ndarray  # (num_years,)
    monthly_spending_schedule: np.ndarray # (num_years,)
    # Ending portfolios (only for successful sims)
    ending_portfolios: np.ndarray    # (num_simulations,)
    # Failure ages (only for failed sims)
    failure_ages: np.ndarray         # ages at which failure occurred
    # Inputs echo
    inputs: SimulationInputs


def run_simulation(inputs: SimulationInputs) -> SimulationResults:
    """
    Run Monte Carlo retirement simulation using vectorized NumPy operations.

    Convention:
    - Each simulation step represents one year.
    - Beginning-of-year withdrawal: withdraw spending from portfolio, then apply returns.
    - After returns, rebalance to target allocation.
    - Once portfolio drops to <= 0, the simulation is marked as failed.

    Portfolio evolution per year:
        portfolio_after_withdrawal = portfolio - annual_spending
        portfolio_after_return = portfolio_after_withdrawal * (1 + portfolio_return)
        portfolio_end_of_year = portfolio_after_return  (rebalanced)
    """
    rng = np.random.default_rng(inputs.seed)

    num_years = inputs.death_age - inputs.retirement_age
    n_sims = inputs.num_simulations

    # Pre-compute annual spending schedule (inflation-adjusted)
    # Length = num_years + 1 to match ages; last entry is 0 (terminal state, no spending)
    annual_spending_base = inputs.monthly_spending * 12
    annual_spending_schedule = np.zeros(num_years + 1)
    for t in range(num_years):
        annual_spending_schedule[t] = annual_spending_base * (1 + inputs.inflation) ** t
    monthly_spending_schedule = annual_spending_schedule / 12

    # Age axis
    ages = np.arange(inputs.retirement_age, inputs.death_age + 1)
    # Portfolio paths: store value at START of each year (and end)
    portfolio_paths = np.zeros((n_sims, num_years + 1))
    portfolio_paths[:, 0] = inputs.initial_portfolio

    # Generate annual returns — normal (default) or block bootstrap (realistic)
    if getattr(inputs, "return_model", "normal") == "bootstrap" and _HAS_BOOTSTRAP:
        try:
            hist = load_history(inputs.bootstrap_history_path) if inputs.bootstrap_history_path else load_history()
            stock_returns, bond_returns = sample_annual_returns(
                rng, n_sims, num_years,
                block_months=int(getattr(inputs, "bootstrap_block_months", 6)),
                history=hist,
                stock_return=inputs.stock_return, stock_std=inputs.stock_std,
                bond_return=inputs.bond_return, bond_std=inputs.bond_std,
            )
        except Exception:
            # graceful fallback to normal if bootstrap fails
            stock_returns = rng.normal(inputs.stock_return, inputs.stock_std, size=(n_sims, num_years))
            bond_returns = rng.normal(inputs.bond_return, inputs.bond_std, size=(n_sims, num_years))
    else:
        stock_returns = rng.normal(inputs.stock_return, inputs.stock_std, size=(n_sims, num_years))
        bond_returns = rng.normal(inputs.bond_return, inputs.bond_std, size=(n_sims, num_years))

    # Portfolio return per simulation per year (before withdrawal)
    portfolio_returns = (
        inputs.stock_allocation * stock_returns
        + (1 - inputs.stock_allocation) * bond_returns
    )

    # Track failures
    failed = np.zeros(n_sims, dtype=bool)
    failure_ages_list = []
    failure_age_map = np.full(n_sims, -1, dtype=int)

    # Run simulation year by year (unavoidable for sequence-of-returns with withdrawal)
    for t in range(num_years):
        current_portfolio = portfolio_paths[:, t].copy()
        spending = annual_spending_schedule[t]

        # Beginning-of-year withdrawal
        portfolio_after_withdrawal = current_portfolio - spending

        # Mark failures: portfolio cannot fund withdrawal
        newly_failed = (portfolio_after_withdrawal <= 0) & (~failed)
        failed |= newly_failed
        failure_age_map[newly_failed] = ages[t]

        # Clamp to zero (don't allow negative to recover)
        portfolio_after_withdrawal = np.maximum(portfolio_after_withdrawal, 0.0)

        # Apply returns
        portfolio_after_return = portfolio_after_withdrawal * (1 + portfolio_returns[:, t])

        # Clamp to zero
        portfolio_after_return = np.maximum(portfolio_after_return, 0.0)

        # Portfolio after rebalancing (value unchanged, just conceptual)
        portfolio_paths[:, t + 1] = portfolio_after_return

    # Extract ending portfolios
    ending_portfolios = portfolio_paths[:, -1]

    # Failure ages (failure_age_map stores age values, not indices into ages)
    failure_ages = failure_age_map[failure_age_map >= 0].astype(float) if np.any(failure_age_map >= 0) else np.array([])

    return SimulationResults(
        portfolio_paths=portfolio_paths,
        failed=failed,
        ages=ages,
        annual_spending_schedule=annual_spending_schedule,
        monthly_spending_schedule=monthly_spending_schedule,
        ending_portfolios=ending_portfolios,
        failure_ages=failure_ages,
        inputs=inputs,
    )


def get_percentile_paths(results: SimulationResults, percentiles: list[float]) -> dict:
    """Calculate percentile portfolio paths across all simulations (including failed)."""
    paths = results.portfolio_paths
    percentile_paths = {}
    for p in percentiles:
        percentile_paths[f"{p:.0f}th"] = np.percentile(paths, p, axis=0)
    return percentile_paths


def get_successful_ending_portfolios(results: SimulationResults) -> np.ndarray:
    """Return ending portfolios for successful simulations only."""
    return results.ending_portfolios[~results.failed]


def get_sensitivity_results(
    base_inputs: SimulationInputs,
    param_name: str,
    param_values: list,
) -> list[dict]:
    """
    Run sensitivity analysis for a single parameter, holding others fixed.
    Returns list of dicts with failure rate for each parameter value.
    """
    results_list = []
    for val in param_values:
        modified = SimulationInputs(**vars(base_inputs))
        setattr(modified, param_name, val)
        sim_result = run_simulation(modified)
        n_failed = int(np.sum(sim_result.failed))
        n_total = modified.num_simulations
        results_list.append({
            param_name: val,
            "failed": n_failed,
            "total": n_total,
            "failure_rate": n_failed / n_total * 100,
            "success_rate": (n_total - n_failed) / n_total * 100,
        })
    return results_list


def find_required_portfolio(
    base_inputs: SimulationInputs,
    target_success_rate: float,
    search_sims: int = 10_000,
    lo: float = 1_000_000_000,
    hi: float = 200_000_000_000,
    tolerance: float = 50_000_000,
    max_iterations: int = 40,
) -> dict:
    """
    Binary search for the minimum portfolio that achieves the target success rate.

    Returns dict with:
        - required_portfolio: the found portfolio value
        - success_rate: actual success rate at that portfolio
        - found: bool, whether search converged
        - iterations: number of search iterations used
    """
    search_inputs = SimulationInputs(**vars(base_inputs))
    search_inputs.num_simulations = search_sims
    target_pct = target_success_rate * 100  # convert 0.90 to 90.0

    iterations = 0
    for _ in range(max_iterations):
        iterations += 1
        mid = (lo + hi) / 2
        search_inputs.initial_portfolio = mid
        result = run_simulation(search_inputs)
        actual_success = (1 - np.mean(result.failed)) * 100

        if actual_success >= target_pct:
            hi = mid
        else:
            lo = mid

        if hi - lo < tolerance:
            break

    final_inputs = SimulationInputs(**vars(base_inputs))
    final_inputs.initial_portfolio = hi
    final_result = run_simulation(final_inputs)
    final_success = (1 - np.mean(final_result.failed)) * 100

    return {
        "required_portfolio": hi,
        "success_rate": final_success,
        "found": final_success >= target_pct,
        "iterations": iterations,
    }


def build_success_rate_curve(
    base_inputs: SimulationInputs,
    center_portfolio: float,
    num_points: int = 20,
    search_sims: int = 10_000,
) -> list[dict]:
    """
    Build a portfolio-vs-success-rate curve around a center portfolio value.
    Returns list of dicts with portfolio and success_rate.
    """
    half_range = max(center_portfolio * 0.5, 2_000_000_000)
    lo = max(500_000_000, center_portfolio - half_range)
    hi = center_portfolio + half_range
    portfolios = np.linspace(lo, hi, num_points)

    curve_inputs = SimulationInputs(**vars(base_inputs))
    curve_inputs.num_simulations = search_sims

    curve = []
    for p in portfolios:
        curve_inputs.initial_portfolio = p
        result = run_simulation(curve_inputs)
        success = (1 - np.mean(result.failed)) * 100
        curve.append({"portfolio": p, "success_rate": success})
    return curve


# ─────────────────────────────────────────────────────────────────────────────
# Accumulation Simulation (saving for retirement)
# ─────────────────────────────────────────────────────────────────────────────

def run_accumulation_simulation(
    initial_portfolio: float,
    monthly_contribution: float,
    stock_allocation: float,
    stock_return: float,
    stock_std: float,
    bond_return: float,
    bond_std: float,
    current_age: int,
    retirement_age: int,
    num_simulations: int,
    seed: int,
    return_model: str = "bootstrap",
    bootstrap_block_months: int = 6,
    bootstrap_history_path: str | None = None,
) -> dict:
    """
    Simulate wealth accumulation from regular contributions.

    Convention (end-of-year contribution, conservative):
        portfolio_end = portfolio_start × (1 + annual_return) + annual_contribution

    This assumes contributions are made at year-end and earn no returns
    in the year they are deposited. This is slightly conservative.

    Returns dict with:
        - portfolio_paths: (num_simulations, num_years + 1)
        - final_portfolios: (num_simulations,)
        - ages: age axis
        - annual_contribution: float
    """
    rng = np.random.default_rng(seed)

    num_years = retirement_age - current_age
    n_sims = num_simulations
    annual_contribution = monthly_contribution * 12

    # Generate returns — normal (default) or block bootstrap (realistic)
    if return_model == "bootstrap" and _HAS_BOOTSTRAP:
        try:
            hist = load_history(bootstrap_history_path) if bootstrap_history_path else load_history()
            stock_returns, bond_returns = sample_annual_returns(
                rng, n_sims, num_years,
                block_months=int(bootstrap_block_months),
                history=hist,
                stock_return=stock_return, stock_std=stock_std,
                bond_return=bond_return, bond_std=bond_std,
            )
        except Exception:
            stock_returns = rng.normal(stock_return, stock_std, size=(n_sims, num_years))
            bond_returns = rng.normal(bond_return, bond_std, size=(n_sims, num_years))
    else:
        stock_returns = rng.normal(stock_return, stock_std, size=(n_sims, num_years))
        bond_returns = rng.normal(bond_return, bond_std, size=(n_sims, num_years))

    portfolio_returns = (
        stock_allocation * stock_returns
        + (1 - stock_allocation) * bond_returns
    )

    # Simulate accumulation
    portfolio = np.full(n_sims, float(initial_portfolio))
    portfolio_paths = np.zeros((n_sims, num_years + 1))
    portfolio_paths[:, 0] = portfolio

    for t in range(num_years):
        portfolio = portfolio * (1 + portfolio_returns[:, t]) + annual_contribution
        portfolio_paths[:, t + 1] = portfolio

    ages = np.arange(current_age, retirement_age + 1)

    return {
        "portfolio_paths": portfolio_paths,
        "final_portfolios": portfolio_paths[:, -1],
        "ages": ages,
        "annual_contribution": annual_contribution,
    }


def find_required_contribution(
    initial_portfolio: float,
    target_portfolio: float,
    stock_allocation: float,
    stock_return: float,
    stock_std: float,
    bond_return: float,
    bond_std: float,
    current_age: int,
    retirement_age: int,
    target_success_rate: float,
    num_simulations: int = 10_000,
    seed: int = 42,
    lo: float = 0,
    hi: float = 50_000_000,
    tolerance: float = 100_000,
    max_iterations: int = 40,
    return_model: str = "bootstrap",
    bootstrap_block_months: int = 6,
    bootstrap_history_path: str | None = None,
) -> dict:
    """
    Binary search for the minimum monthly contribution that achieves the
    target probability of reaching the target portfolio.

    Returns dict with:
        - required_monthly_contribution: the found contribution
        - success_rate: actual probability at that contribution
        - found: bool, whether search converged
        - iterations: number of search iterations used
    """
    target_pct = target_success_rate * 100

    iterations = 0
    for _ in range(max_iterations):
        iterations += 1
        mid = (lo + hi) / 2
        result = run_accumulation_simulation(
            initial_portfolio=initial_portfolio,
            monthly_contribution=mid,
            stock_allocation=stock_allocation,
            stock_return=stock_return,
            stock_std=stock_std,
            bond_return=bond_return,
            bond_std=bond_std,
            current_age=current_age,
            retirement_age=retirement_age,
            num_simulations=num_simulations,
            seed=seed,
            return_model=return_model,
            bootstrap_block_months=bootstrap_block_months,
            bootstrap_history_path=bootstrap_history_path,
        )
        actual_success = np.mean(result["final_portfolios"] >= target_portfolio) * 100

        if actual_success >= target_pct:
            hi = mid
        else:
            lo = mid

        if hi - lo < tolerance:
            break

    # Final run at hi
    final_result = run_accumulation_simulation(
        initial_portfolio=initial_portfolio,
        monthly_contribution=hi,
        stock_allocation=stock_allocation,
        stock_return=stock_return,
        stock_std=stock_std,
        bond_return=bond_return,
        bond_std=bond_std,
        current_age=current_age,
        retirement_age=retirement_age,
        num_simulations=num_simulations,
        seed=seed,
        return_model=return_model,
        bootstrap_block_months=bootstrap_block_months,
        bootstrap_history_path=bootstrap_history_path,
    )
    final_success = np.mean(final_result["final_portfolios"] >= target_portfolio) * 100

    return {
        "required_monthly_contribution": hi,
        "success_rate": final_success,
        "found": final_success >= target_pct,
        "iterations": iterations,
    }


def build_contribution_curve(
    initial_portfolio: float,
    target_portfolio: float,
    stock_allocation: float,
    stock_return: float,
    stock_std: float,
    bond_return: float,
    bond_std: float,
    current_age: int,
    retirement_age: int,
    num_points: int = 20,
    num_simulations: int = 10_000,
    seed: int = 42,
    return_model: str = "bootstrap",
    bootstrap_block_months: int = 6,
    bootstrap_history_path: str | None = None,
) -> list[dict]:
    """
    Build a monthly-contribution-vs-success-rate curve.
    Returns list of dicts with contribution and success_rate.
    """
    contributions = np.linspace(0, 30_000_000, num_points)

    curve = []
    for c in contributions:
        result = run_accumulation_simulation(
            initial_portfolio=initial_portfolio,
            monthly_contribution=c,
            stock_allocation=stock_allocation,
            stock_return=stock_return,
            stock_std=stock_std,
            bond_return=bond_return,
            bond_std=bond_std,
            current_age=current_age,
            retirement_age=retirement_age,
            num_simulations=num_simulations,
            seed=seed,
            return_model=return_model,
            bootstrap_block_months=bootstrap_block_months,
            bootstrap_history_path=bootstrap_history_path,
        )
        success = np.mean(result["final_portfolios"] >= target_portfolio) * 100
        curve.append({"contribution": c, "success_rate": success})
    return curve
