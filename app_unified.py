"""
Unified Retirement Planning Dashboard

A single Streamlit application that answers all three retirement questions:
1. Will my money last? (Decumulation simulation)
2. How much do I need to retire? (Target portfolio finder)
3. How much should I save monthly? (Accumulation target finder)
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from simulation import (
    SimulationInputs,
    run_simulation,
    get_percentile_paths,
    get_successful_ending_portfolios,
    get_sensitivity_results,
    find_required_portfolio,
    build_success_rate_curve,
    run_accumulation_simulation,
    find_required_contribution,
    build_contribution_curve,
)

# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def fmt_idr(value: float) -> str:
    if abs(value) >= 1e12:
        return f"Rp{value / 1e12:,.1f}T"
    if abs(value) >= 1e9:
        return f"Rp{value / 1e9:,.1f}B"
    return f"Rp{value / 1e6:,.0f}M"

def fmt_pct(value: float) -> str:
    return f"{value:,.2f}%"

# ─────────────────────────────────────────────────────────────────────────────
# Shared Chart Helpers
# ─────────────────────────────────────────────────────────────────────────────

def plot_sample_paths(ages, paths, failed, n_display=100, height=450):
    fig = go.Figure()
    indices = np.random.choice(len(paths), size=min(n_display, len(paths)), replace=False)
    for idx in indices:
        color = "#ef5350" if failed[idx] else "#42a5f5"
        fig.add_trace(go.Scatter(
            x=ages, y=paths[idx], mode="lines",
            line=dict(width=0.8, color=color), opacity=0.15,
            showlegend=False, hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                             line=dict(color="#42a5f5", width=2), name="Successful"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                             line=dict(color="#ef5350", width=2), name="Failed"))
    fig.update_layout(xaxis_title="Age", yaxis_title="Portfolio Value (IDR)",
                      yaxis=dict(tickformat=",.0f"), template="plotly_white",
                      height=height,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def plot_ending_distribution(ending_portfolios, failed, height=400):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=ending_portfolios[~failed], name="Successful",
                               marker_color="#42a5f5", opacity=0.7, nbinsx=80))
    fig.add_trace(go.Histogram(x=ending_portfolios[failed], name="Failed (portfolio = 0)",
                               marker_color="#ef5350", opacity=0.7, nbinsx=20))
    fig.update_layout(barmode="overlay", xaxis_title="Ending Portfolio Value (IDR)",
                      yaxis_title="Frequency", xaxis=dict(tickformat=",.0f"),
                      template="plotly_white", height=height,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def plot_donut(success, failure, height=350):
    fig = go.Figure(data=[go.Pie(
        labels=["Successful", "Failed"], values=[success, failure], hole=0.55,
        marker=dict(colors=["#42a5f5", "#ef5350"]), textinfo="label+percent", textfont_size=14,
    )])
    fig.update_layout(template="plotly_white", height=height, showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
    return fig

def plot_percentile_paths(ages, results, height=450):
    percentile_paths = get_percentile_paths(results, [5, 25, 50, 75, 95])
    colors_p = {"5th": "#ef5350", "25th": "#ffa726", "50th": "#66bb6a", "75th": "#42a5f5", "95th": "#7e57c2"}
    fig = go.Figure()
    for label, path in percentile_paths.items():
        fig.add_trace(go.Scatter(x=ages, y=path, mode="lines", name=f"{label} Percentile",
                                 line=dict(width=2.5, color=colors_p.get(label, "#999"))))
    fig.update_layout(xaxis_title="Age", yaxis_title="Portfolio Value (IDR)",
                      yaxis=dict(tickformat=",.0f"), template="plotly_white", height=height,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def plot_spending_schedule(ages, annual_spending, monthly_spending, height=400):
    df = pd.DataFrame({"Age": ages, "Annual": annual_spending, "Monthly": monthly_spending})
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df["Age"], y=df["Annual"], name="Annual Spending",
                         marker_color="#42a5f5", opacity=0.7), secondary_y=False)
    fig.add_trace(go.Scatter(x=df["Age"], y=df["Monthly"], name="Monthly Spending",
                             mode="lines+markers", line=dict(color="#ef5350", width=2)), secondary_y=True)
    fig.update_layout(template="plotly_white", height=height,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text="Annual Spending (IDR)", tickformat=",.0f", secondary_y=False)
    fig.update_yaxes(title_text="Monthly Spending (IDR)", tickformat=",.0f", secondary_y=True)
    fig.update_xaxes(title_text="Age")
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# Page Config & Title
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Retirement Planning Dashboard", page_icon=" retirement", layout="wide")
st.title("Retirement Planning Dashboard")
st.markdown("Answer all three retirement questions in one place using Monte Carlo simulation.")
# Model badge is rendered in sidebar toggle; reflect current choice in top bar if bootstrap active
# (achieved via sidebar variables return_model / bootstrap_block_months — placeholder for lint)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Shared Inputs
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Model Assumptions")
    st.caption("Engine: Block Bootstrap over 123y of DMS-anchored monthly history "
               "(joint stock+bond blocks, preserves crashes and correlation).")

    st.subheader("Asset Allocation")
    stock_allocation = st.slider(
        "International Stocks Allocation", min_value=0, max_value=100, value=60, step=5, format="%d%%",
    ) / 100
    bond_allocation = 1 - stock_allocation
    st.markdown(f"**International Stocks:** {stock_allocation*100:.0f}%  \n"
                f"**Indonesian Bonds (SBN):** {bond_allocation*100:.0f}%")

    st.subheader("Market History")
    import os as _os
    _market_path = _os.path.join(_os.path.dirname(__file__), "data", "history_market.csv")
    _market_ok = _os.path.exists(_market_path)
    if _market_ok:
        _hist = pd.read_csv(_market_path, parse_dates=["date"])
        _s, _b = _hist["stock_ret"], _hist["bond_ret"]
        _n = len(_hist)
        st.markdown(
            f"**DMS-anchored, SBN bond leg**  \n"
            f"{_n} months ({_hist['date'].min().date()} → {_hist['date'].max().date()})  \n"
            f"Stocks: {((1 + _s).prod() ** (12 / _n) - 1) * 100:.1f}% CAGR, "
            f"{_s.std() * (12 ** 0.5) * 100:.1f}% vol  \n"
            f"SBN bonds: {((1 + _b).prod() ** (12 / _n) - 1) * 100:.1f}% CAGR, "
            f"{_b.std() * (12 ** 0.5) * 100:.1f}% vol  \n"
            f"Stock–bond corr: {_s.corr(_b):.2f}"
        )
    else:
        st.warning("`data/history_market.csv` not found — falling back to Normal (i.i.d.).")
    # Return/volatility sliders removed: Block Bootstrap samples real monthly
    # blocks, so assumed mean/vol inputs are ignored by the engine.

    st.subheader("Simulation Settings")
    num_simulations = st.slider(
        "Number of Simulations", min_value=2_000, max_value=100_000, value=10_000, step=1_000,
    )
    seed = st.number_input("Random Seed", min_value=0, max_value=99999, value=42, step=1,
                           help="Same seed = reproducible results.")
    bootstrap_block_months = st.select_slider(
        "Block size (months)", options=[3, 6, 12], value=6,
        help="Block bootstrap: larger blocks preserve more autocorrelation / vol clustering. 6 recommended.",
    )

    if _market_ok:
        return_model, bootstrap_history_path = "bootstrap", _market_path
    else:
        return_model, bootstrap_history_path = "normal", None
        st.warning("Market history missing — using Normal fallback.")
    # Fixed engine params (informational only — Block Bootstrap ignores assumed
    # mean/vol and samples joint monthly blocks from history instead).
    stock_return, stock_std = 0.072, 0.17
    bond_return, bond_std = 0.06, 0.115

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "Will My Money Last?",
    "How Much Do I Need?",
    "How Much Should I Save?",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1: Will My Money Last? (Decumulation)
# ═════════════════════════════════════════════════════════════════════════════

with tab1:
    st.header("Will My Money Last?")
    st.markdown("Simulate whether your retirement portfolio can sustain inflation-adjusted spending.")

    t1_col1, t1_col2 = st.columns(2)
    with t1_col1:
        t1_current_age = st.slider(
            "Current Age", min_value=20, max_value=60, value=30, step=1, key="t1_cage",
        )
        monthly_spending_m = st.slider(
            "Initial Monthly Retirement Spending (Today's Money)", min_value=5, max_value=50, value=20, step=1,
            format="Rp%dM", key="t1_spend",
            help="Monthly spending in today's purchasing power. Will be adjusted for inflation until retirement.",
        )
        inflation = st.slider(
            "Annual Inflation", min_value=1.0, max_value=5.0, value=3.0, step=0.1, format="%.1f%%", key="t1_infl",
        ) / 100
    with t1_col2:
        retirement_age = st.slider(
            "Retirement Age", min_value=30, max_value=70, value=60, step=1, key="t1_retire",
        )
        death_age = st.slider(
            "Planning / Death Age", min_value=60, max_value=100, value=85, step=1, key="t1_death",
        )

    initial_portfolio_m = st.slider(
        "Initial Retirement Portfolio", min_value=1_000, max_value=20_000, value=10_000, step=500,
        format="Rp%dM", key="t1_portfolio",
    )

    if death_age <= retirement_age:
        st.error(f"Planning/death age ({death_age}) must be greater than retirement age ({retirement_age}).")
        st.stop()
    if retirement_age <= t1_current_age:
        st.error(f"Retirement age ({retirement_age}) must be greater than current age ({t1_current_age}).")
        st.stop()

    years_to_retirement = retirement_age - t1_current_age
    actual_monthly_at_retirement = monthly_spending_m * (1 + inflation) ** years_to_retirement

    inputs1 = SimulationInputs(
        initial_portfolio=float(initial_portfolio_m * 1_000_000),
        monthly_spending=float(actual_monthly_at_retirement * 1_000_000),
        inflation=inflation,
        stock_allocation=stock_allocation,
        stock_return=stock_return, stock_std=stock_std,
        bond_return=bond_return, bond_std=bond_std,
        retirement_age=retirement_age, death_age=death_age,
        num_simulations=num_simulations, seed=seed,
        return_model=return_model, bootstrap_block_months=bootstrap_block_months,
        bootstrap_history_path=bootstrap_history_path,
    )
    results1 = run_simulation(inputs1)

    n_failed = int(np.sum(results1.failed))
    n_success = num_simulations - n_failed
    failure_rate = n_failed / num_simulations * 100
    success_rate = n_success / num_simulations * 100
    annual_spending_initial = actual_monthly_at_retirement * 1_000_000 * 12
    withdrawal_rate = annual_spending_initial / (initial_portfolio_m * 1_000_000) * 100

    st.divider()
    st.subheader("Summary")
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    s_col1.metric("Initial Portfolio", fmt_idr(initial_portfolio_m * 1_000_000))
    s_col2.metric("Monthly Spending (Today's Money)", f"Rp{monthly_spending_m}M/month")
    s_col3.metric("Allocation", f"{stock_allocation*100:.0f}% Stocks / {bond_allocation*100:.0f}% Bonds")
    s_col4.metric("Retirement Period", f"Age {retirement_age} to {death_age} ({death_age - retirement_age} yrs)")

    st.info(f"**Spending adjusted for {years_to_retirement} years of inflation:** "
            f"Rp{monthly_spending_m}M today → **Rp{actual_monthly_at_retirement:.1f}M/month** at retirement "
            f"(age {retirement_age})")

    st.divider()
    st.subheader("Primary Results")
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    r_col1.metric("Failed Simulations", f"{n_failed:,} / {num_simulations:,}")
    r_col2.metric("Failure Rate", fmt_pct(failure_rate))
    r_col3.metric("Success Rate", fmt_pct(success_rate))
    r_col4.metric("Initial Withdrawal Rate", fmt_pct(withdrawal_rate))

    i_col1, i_col2, i_col3 = st.columns(3)
    i_col1.metric("Retirement Duration", f"{death_age - retirement_age} years")
    i_col2.metric("Initial Annual Spending (at Retirement)", fmt_idr(annual_spending_initial))
    final_spending = annual_spending_initial * (1 + inflation) ** (death_age - retirement_age - 1)
    i_col3.metric("Final Year Spending", fmt_idr(final_spending))

    st.divider()
    st.subheader("Ending Portfolio Statistics")
    success_portfolios = get_successful_ending_portfolios(results1)
    all_portfolios = results1.ending_portfolios

    stat_c1, stat_c2 = st.columns(2)
    with stat_c1:
        st.markdown("**Among Successful Simulations**")
        if len(success_portfolios) > 0:
            stats_s = {"Mean": fmt_idr(np.mean(success_portfolios)),
                       "Median": fmt_idr(np.median(success_portfolios)),
                       "5th Percentile": fmt_idr(np.percentile(success_portfolios, 5)),
                       "25th Percentile": fmt_idr(np.percentile(success_portfolios, 25)),
                       "75th Percentile": fmt_idr(np.percentile(success_portfolios, 75)),
                       "95th Percentile": fmt_idr(np.percentile(success_portfolios, 95)),
                       "Minimum": fmt_idr(np.min(success_portfolios))}
        else:
            stats_s = {"(No successful simulations)": "—"}
        st.dataframe(pd.DataFrame(stats_s.items(), columns=["Metric", "Value"]),
                     use_container_width=True, hide_index=True)
    with stat_c2:
        st.markdown("**Across All Simulations**")
        stats_all = {"Mean": fmt_idr(np.mean(all_portfolios)),
                     "Median": fmt_idr(np.median(all_portfolios)),
                     "5th Percentile": fmt_idr(np.percentile(all_portfolios, 5)),
                     "25th Percentile": fmt_idr(np.percentile(all_portfolios, 25)),
                     "75th Percentile": fmt_idr(np.percentile(all_portfolios, 75)),
                     "95th Percentile": fmt_idr(np.percentile(all_portfolios, 95))}
        st.dataframe(pd.DataFrame(stats_all.items(), columns=["Metric", "Value"]),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Charts")
    st.markdown("#### Simulated Portfolio Paths (sample of 100)")
    st.plotly_chart(plot_sample_paths(results1.ages, results1.portfolio_paths, results1.failed),
                    use_container_width=True, key="t1_sample_paths")

    st.markdown("#### Ending Portfolio Distribution")
    st.plotly_chart(plot_ending_distribution(all_portfolios, results1.failed), use_container_width=True, key="t1_ending_dist")

    st.markdown("#### Success vs Failure")
    st.plotly_chart(plot_donut(n_success, n_failed), use_container_width=True, key="t1_donut")

    st.markdown("#### Percentile Portfolio Paths")
    st.plotly_chart(plot_percentile_paths(results1.ages, results1), use_container_width=True, key="t1_pctl_paths")

    st.divider()
    st.subheader("Inflation-Adjusted Spending Schedule")
    st.plotly_chart(plot_spending_schedule(
        results1.ages[:-1], results1.annual_spending_schedule[:-1], results1.monthly_spending_schedule[:-1]),
        use_container_width=True, key="t1_spending")

    with st.expander("View Spending Schedule Table"):
        spend_df = pd.DataFrame({
            "Age": results1.ages[:-1],
            "Annual Spending (IDR)": results1.annual_spending_schedule[:-1],
            "Monthly Spending (IDR)": results1.monthly_spending_schedule[:-1],
        })
        st.dataframe(spend_df.style.format({
            "Annual Spending (IDR)": "Rp{:,.0f}", "Monthly Spending (IDR)": "Rp{:,.0f}",
        }), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Risk Metrics")
    median_failure_age = float(np.median(results1.failure_ages)) if n_failed > 0 else None
    total_nominal = float(np.sum(results1.annual_spending_schedule))

    rm_c1, rm_c2 = st.columns(2)
    with rm_c1:
        st.metric("Failure Probability", fmt_pct(failure_rate))
        st.metric("Success Probability", fmt_pct(success_rate))
        st.metric("Median Ending Portfolio", fmt_idr(np.median(all_portfolios)))
        st.metric("5th Percentile Ending Portfolio", fmt_idr(np.percentile(all_portfolios, 5)))
    with rm_c2:
        st.metric("Initial Withdrawal Rate", fmt_pct(withdrawal_rate))
        st.metric("Maximum Annual Spending", fmt_idr(np.max(results1.annual_spending_schedule)))
        st.metric("Total Nominal Withdrawals", fmt_idr(total_nominal))
        st.metric("Median Age at Failure", f"{median_failure_age:.0f}" if median_failure_age else "N/A (no failures)")

    st.divider()
    st.subheader("Sensitivity Analysis")
    st.markdown("See how the failure rate changes when one assumption is varied, holding all others fixed.")
    sens_target = st.selectbox("Variable to Analyze",
                               ["Initial Portfolio", "Inflation", "Stock Allocation", "Monthly Spending"],
                               key="t1_sens")

    if sens_target == "Initial Portfolio":
        pvals = [v * 1_000_000 for v in range(5_000, 20_500, 1_000)]
        pname = "initial_portfolio"
        pdisp = [fmt_idr(v) for v in pvals]
    elif sens_target == "Inflation":
        pvals = [v / 100 for v in range(1, 6)]
        pname = "inflation"
        pdisp = [f"{v*100:.1f}%" for v in pvals]
    elif sens_target == "Stock Allocation":
        pvals = [v / 100 for v in range(0, 101, 10)]
        pname = "stock_allocation"
        pdisp = [f"{v*100:.0f}%" for v in pvals]
    else:
        pvals = [v * 1_000_000 for v in range(10, 55, 5)]
        pname = "monthly_spending"
        pdisp = [fmt_idr(v) for v in pvals]

    sens_inputs = SimulationInputs(**vars(inputs1))
    sens_inputs.num_simulations = min(5_000, num_simulations)
    with st.spinner(f"Running sensitivity analysis for {sens_target}..."):
        sens = get_sensitivity_results(sens_inputs, pname, pvals)
    sens_df = pd.DataFrame(sens)
    sens_df["label"] = pdisp
    sens_df = sens_df[["label", "failed", "total", "failure_rate", "success_rate"]]
    sens_df.columns = [sens_target, "Failed", "Total", "Failure Rate (%)", "Success Rate (%)"]
    st.dataframe(sens_df, use_container_width=True, hide_index=True)

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Bar(x=sens_df[sens_target], y=sens_df["Failure Rate (%)"],
                              name="Failure Rate", marker_color="#ef5350"))
    fig_sens.add_trace(go.Scatter(x=sens_df[sens_target], y=sens_df["Success Rate (%)"],
                                  name="Success Rate", mode="lines+markers",
                                  line=dict(color="#42a5f5", width=2)))
    fig_sens.update_layout(xaxis_title=sens_target, yaxis_title="Rate (%)",
                           template="plotly_white", height=400,
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_sens, use_container_width=True, key="t1_sens_chart")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2: How Much Do I Need? (Target Portfolio Finder)
# ═════════════════════════════════════════════════════════════════════════════

with tab2:
    st.header("How Much Do I Need to Retire?")
    st.markdown("Specify your desired lifestyle and find the minimum portfolio required.")

    t2_c1, t2_c2 = st.columns(2)
    with t2_c1:
        t2_current_age = st.slider(
            "Current Age", min_value=20, max_value=60, value=30, step=1, key="t2_cage",
        )
        t2_spend_m = st.slider(
            "Initial Monthly Retirement Spending (Today's Money)", min_value=5, max_value=50, value=20, step=1,
            format="Rp%dM", key="t2_spend",
            help="Monthly spending in today's purchasing power. Will be adjusted for inflation until retirement.",
        )
        t2_infl = st.slider(
            "Annual Inflation", min_value=1.0, max_value=5.0, value=3.0, step=0.1, format="%.1f%%", key="t2_infl",
        ) / 100
    with t2_c2:
        t2_retire = st.slider(
            "Retirement Age", min_value=30, max_value=70, value=60, step=1, key="t2_retire",
        )
        t2_death = st.slider(
            "Planning / Death Age", min_value=60, max_value=100, value=85, step=1, key="t2_death",
        )

    t2_target_pct = st.slider(
        "Target Success Rate", min_value=70, max_value=99, value=90, step=1, format="%d%%", key="t2_target",
        help="Minimum acceptable success rate. The system finds the smallest portfolio achieving at least this rate.",
    ) / 100

    if t2_death <= t2_retire:
        st.error(f"Planning/death age ({t2_death}) must be greater than retirement age ({t2_retire}).")
        st.stop()
    if t2_retire <= t2_current_age:
        st.error(f"Retirement age ({t2_retire}) must be greater than current age ({t2_current_age}).")
        st.stop()

    t2_years_to_retirement = t2_retire - t2_current_age
    t2_actual_monthly = t2_spend_m * (1 + t2_infl) ** t2_years_to_retirement

    inputs2 = SimulationInputs(
        initial_portfolio=10_000_000_000,
        monthly_spending=float(t2_actual_monthly * 1_000_000),
        inflation=t2_infl,
        stock_allocation=stock_allocation,
        stock_return=stock_return, stock_std=stock_std,
        bond_return=bond_return, bond_std=bond_std,
        retirement_age=t2_retire, death_age=t2_death,
        num_simulations=num_simulations, seed=seed,
        return_model=return_model, bootstrap_block_months=bootstrap_block_months,
        bootstrap_history_path=bootstrap_history_path,
    )

    with st.spinner("Finding the minimum required portfolio..."):
        search2 = find_required_portfolio(inputs2, target_success_rate=t2_target_pct, search_sims=10_000)

    required_portfolio = search2["required_portfolio"]
    found2 = search2["found"]

    if not found2:
        st.warning(f"Could not achieve {t2_target_pct*100:.0f}% success rate even with Rp200B. "
                   "Consider reducing spending, lowering the target, or shortening the horizon.")

    inputs2.initial_portfolio = required_portfolio
    results2 = run_simulation(inputs2)

    n2_failed = int(np.sum(results2.failed))
    n2_success = num_simulations - n2_failed
    failure_rate2 = n2_failed / num_simulations * 100
    success_rate2 = n2_success / num_simulations * 100
    annual2 = t2_actual_monthly * 1_000_000 * 12
    withdrawal2 = annual2 / required_portfolio * 100

    st.divider()
    st.subheader("Summary")
    s2_c1, s2_c2, s2_c3, s2_c4 = st.columns(4)
    s2_c1.metric("Required Portfolio", fmt_idr(required_portfolio))
    s2_c2.metric("Monthly Spending (Today's Money)", f"Rp{t2_spend_m}M/month")
    s2_c3.metric("Allocation", f"{stock_allocation*100:.0f}% Stocks / {bond_allocation*100:.0f}% Bonds")
    s2_c4.metric("Retirement Period", f"Age {t2_retire} to {t2_death} ({t2_death - t2_retire} yrs)")

    st.info(f"**Spending adjusted for {t2_years_to_retirement} years of inflation:** "
            f"Rp{t2_spend_m}M today → **Rp{t2_actual_monthly:.1f}M/month** at retirement "
            f"(age {t2_retire})")

    st.divider()
    st.subheader("Primary Results")
    r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
    r2_c1.metric("Required Portfolio", fmt_idr(required_portfolio))
    r2_c2.metric("Actual Success Rate", fmt_pct(success_rate2))
    r2_c3.metric("Target Success Rate", fmt_pct(t2_target_pct * 100))
    r2_c4.metric("Initial Withdrawal Rate", fmt_pct(withdrawal2))

    i2_c1, i2_c2, i2_c3 = st.columns(3)
    i2_c1.metric("Retirement Duration", f"{t2_death - t2_retire} years")
    i2_c2.metric("Initial Annual Spending (at Retirement)", fmt_idr(annual2))
    final2 = annual2 * (1 + t2_infl) ** (t2_death - t2_retire - 1)
    i2_c3.metric("Final Year Spending", fmt_idr(final2))

    st.divider()
    st.subheader("Portfolio vs Success Rate")
    with st.spinner("Building success rate curve..."):
        curve2 = build_success_rate_curve(inputs2, center_portfolio=required_portfolio,
                                          num_points=20, search_sims=10_000)
    curve_df2 = pd.DataFrame(curve2)

    fig_c2 = go.Figure()
    fig_c2.add_trace(go.Scatter(x=curve_df2["portfolio"], y=curve_df2["success_rate"],
                                mode="lines+markers", name="Success Rate",
                                line=dict(color="#42a5f5", width=3), marker=dict(size=8)))
    fig_c2.add_hline(y=t2_target_pct * 100, line_dash="dash", line_color="#ef5350",
                     annotation_text=f"Target: {t2_target_pct*100:.0f}%", annotation_position="top left")
    fig_c2.add_vline(x=required_portfolio, line_dash="dash", line_color="#66bb6a",
                     annotation_text=f"Required: {fmt_idr(required_portfolio)}", annotation_position="top right")
    fig_c2.update_layout(xaxis_title="Portfolio Value (IDR)", yaxis_title="Success Rate (%)",
                         xaxis=dict(tickformat=",.0f"), yaxis=dict(range=[0, 105]),
                         template="plotly_white", height=450, showlegend=False)
    st.plotly_chart(fig_c2, use_container_width=True, key="t2_success_curve")

    st.info(f"**Required portfolio for {t2_target_pct*100:.0f}% success rate: {fmt_idr(required_portfolio)}** "
            f"(initial withdrawal rate: {fmt_pct(withdrawal2)})")

    st.divider()
    st.subheader("Ending Portfolio Statistics")
    succ2 = get_successful_ending_portfolios(results2)
    all2 = results2.ending_portfolios

    sc2_1, sc2_2 = st.columns(2)
    with sc2_1:
        st.markdown("**Among Successful Simulations**")
        if len(succ2) > 0:
            ss2 = {"Mean": fmt_idr(np.mean(succ2)), "Median": fmt_idr(np.median(succ2)),
                   "5th Percentile": fmt_idr(np.percentile(succ2, 5)),
                   "25th Percentile": fmt_idr(np.percentile(succ2, 25)),
                   "75th Percentile": fmt_idr(np.percentile(succ2, 75)),
                   "95th Percentile": fmt_idr(np.percentile(succ2, 95)),
                   "Minimum": fmt_idr(np.min(succ2))}
        else:
            ss2 = {"(No successful simulations)": "—"}
        st.dataframe(pd.DataFrame(ss2.items(), columns=["Metric", "Value"]),
                     use_container_width=True, hide_index=True)
    with sc2_2:
        st.markdown("**Across All Simulations**")
        sa2 = {"Mean": fmt_idr(np.mean(all2)), "Median": fmt_idr(np.median(all2)),
               "5th Percentile": fmt_idr(np.percentile(all2, 5)),
               "25th Percentile": fmt_idr(np.percentile(all2, 25)),
               "75th Percentile": fmt_idr(np.percentile(all2, 75)),
               "95th Percentile": fmt_idr(np.percentile(all2, 95))}
        st.dataframe(pd.DataFrame(sa2.items(), columns=["Metric", "Value"]),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Charts")
    st.markdown("#### Simulated Portfolio Paths (sample of 100)")
    st.plotly_chart(plot_sample_paths(results2.ages, results2.portfolio_paths, results2.failed),
                    use_container_width=True, key="t2_sample_paths")

    st.markdown("#### Ending Portfolio Distribution")
    st.plotly_chart(plot_ending_distribution(all2, results2.failed), use_container_width=True, key="t2_ending_dist")

    st.markdown("#### Success vs Failure")
    st.plotly_chart(plot_donut(n2_success, n2_failed), use_container_width=True, key="t2_donut")

    st.markdown("#### Percentile Portfolio Paths")
    st.plotly_chart(plot_percentile_paths(results2.ages, results2), use_container_width=True, key="t2_pctl_paths")

    st.divider()
    st.subheader("Inflation-Adjusted Spending Schedule")
    st.plotly_chart(plot_spending_schedule(
        results2.ages[:-1], results2.annual_spending_schedule[:-1], results2.monthly_spending_schedule[:-1]),
        use_container_width=True, key="t2_spending")

    with st.expander("View Spending Schedule Table"):
        spd2 = pd.DataFrame({"Age": results2.ages[:-1],
                             "Annual Spending (IDR)": results2.annual_spending_schedule[:-1],
                             "Monthly Spending (IDR)": results2.monthly_spending_schedule[:-1]})
        st.dataframe(spd2.style.format({"Annual Spending (IDR)": "Rp{:,.0f}",
                                         "Monthly Spending (IDR)": "Rp{:,.0f}"}),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Risk Metrics")
    mf2 = float(np.median(results2.failure_ages)) if n2_failed > 0 else None
    tn2 = float(np.sum(results2.annual_spending_schedule))

    rm2_c1, rm2_c2 = st.columns(2)
    with rm2_c1:
        st.metric("Failure Probability", fmt_pct(failure_rate2))
        st.metric("Success Probability", fmt_pct(success_rate2))
        st.metric("Median Ending Portfolio", fmt_idr(np.median(all2)))
        st.metric("5th Percentile Ending Portfolio", fmt_idr(np.percentile(all2, 5)))
    with rm2_c2:
        st.metric("Initial Withdrawal Rate", fmt_pct(withdrawal2))
        st.metric("Maximum Annual Spending", fmt_idr(np.max(results2.annual_spending_schedule)))
        st.metric("Total Nominal Withdrawals", fmt_idr(tn2))
        st.metric("Median Age at Failure", f"{mf2:.0f}" if mf2 else "N/A (no failures)")

    st.divider()
    st.subheader("Sensitivity Analysis")
    st.markdown("See how the **required portfolio** changes when one assumption varies.")
    sens2_target = st.selectbox("Variable to Analyze",
                                ["Monthly Spending", "Inflation", "Stock Allocation", "Retirement Age", "Death Age"],
                                key="t2_sens")

    if sens2_target == "Monthly Spending":
        pv2 = [v * 1_000_000 for v in range(10, 55, 5)]
        pn2 = "monthly_spending"
        pd2 = [fmt_idr(v) for v in pv2]
    elif sens2_target == "Inflation":
        pv2 = [v / 100 for v in range(1, 6)]
        pn2 = "inflation"
        pd2 = [f"{v*100:.1f}%" for v in pv2]
    elif sens2_target == "Stock Allocation":
        pv2 = [v / 100 for v in range(0, 101, 10)]
        pn2 = "stock_allocation"
        pd2 = [f"{v*100:.0f}%" for v in pv2]
    elif sens2_target == "Retirement Age":
        pv2 = list(range(40, 66, 5))
        pn2 = "retirement_age"
        pd2 = [str(v) for v in pv2]
    else:
        pv2 = list(range(75, 96, 5))
        pn2 = "death_age"
        pd2 = [str(v) for v in pv2]

    with st.spinner(f"Running sensitivity analysis for {sens2_target}..."):
        sr2 = []
        for val in pv2:
            mod = SimulationInputs(**vars(inputs2))
            setattr(mod, pn2, val)
            ca = getattr(mod, "retirement_age", t2_retire) if pn2 == "death_age" else t2_retire
            ra = getattr(mod, "retirement_age", t2_retire)
            da = getattr(mod, "death_age", t2_death)
            if pn2 == "retirement_age":
                ra = val
            if pn2 == "death_age":
                da = val
            if da <= ra:
                sr2.append({sens2_target: val, "Required Portfolio": None, "Actual Success Rate": None, "Found": False})
                continue
            res = find_required_portfolio(mod, target_success_rate=t2_target_pct, search_sims=10_000)
            sr2.append({sens2_target: val, "Required Portfolio": res["required_portfolio"],
                        "Actual Success Rate": res["success_rate"], "Found": res["found"]})

    s2df = pd.DataFrame(sr2)
    s2df["label"] = pd2[:len(s2df)]
    valid2 = s2df.dropna(subset=["Required Portfolio"])
    disp2 = pd.DataFrame()
    disp2["label"] = valid2["label"].values
    disp2["Required Portfolio"] = valid2["Required Portfolio"].apply(lambda x: fmt_idr(x) if pd.notna(x) else "N/A")
    disp2["Success Rate"] = valid2["Actual Success Rate"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
    st.dataframe(disp2, use_container_width=True, hide_index=True)

    if len(valid2) > 0:
        fig_s2 = go.Figure()
        fig_s2.add_trace(go.Bar(x=disp2["label"], y=valid2["Required Portfolio"],
                                name="Required Portfolio", marker_color="#42a5f5",
                                text=disp2["Required Portfolio"], textposition="outside"))
        fig_s2.update_layout(xaxis_title=sens2_target, yaxis_title="Required Portfolio (IDR)",
                             yaxis=dict(tickformat=",.0f"), template="plotly_white",
                             height=450, showlegend=False)
        st.plotly_chart(fig_s2, use_container_width=True, key="t2_sens_chart")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3: How Much Should I Save? (Accumulation Target Finder)
# ═════════════════════════════════════════════════════════════════════════════

with tab3:
    st.header("How Much Should I Save Monthly?")
    st.markdown("Want a target portfolio at retirement? Find the monthly contribution you need.")

    t3_c1, t3_c2 = st.columns(2)
    with t3_c1:
        t3_current_age = st.slider("Current Age", min_value=20, max_value=60, value=25, step=1, key="t3_cage")
        t3_retire_age = st.slider("Retirement Age", min_value=30, max_value=70, value=60, step=1, key="t3_rage")
    with t3_c2:
        t3_init_m = st.slider(
            "Initial Savings", min_value=0, max_value=100, value=10, step=5,
            format="Rp%dM", key="t3_init",
            help="How much you already have saved today.",
        )
        t3_target_m = st.slider(
            "Target Retirement Portfolio", min_value=1_000, max_value=20_000, value=10_000, step=500,
            format="Rp%dM", key="t3_target",
            help="How much you want to have at retirement.",
        )

    t3_prob = st.slider(
        "Target Probability of Reaching Goal", min_value=50, max_value=99, value=90, step=1, format="%d%%",
        key="t3_prob",
        help="The system finds the smallest monthly contribution achieving at least this probability.",
    ) / 100

    if t3_retire_age <= t3_current_age:
        st.error(f"Retirement age ({t3_retire_age}) must be greater than current age ({t3_current_age}).")
        st.stop()

    t3_init = t3_init_m * 1_000_000
    t3_target = t3_target_m * 1_000_000
    t3_years = t3_retire_age - t3_current_age

    with st.spinner("Finding the required monthly contribution..."):
        search3 = find_required_contribution(
            initial_portfolio=t3_init, target_portfolio=t3_target,
            stock_allocation=stock_allocation,
            stock_return=stock_return, stock_std=stock_std,
            bond_return=bond_return, bond_std=bond_std,
            current_age=t3_current_age, retirement_age=t3_retire_age,
            target_success_rate=t3_prob, num_simulations=10_000, seed=seed,
            return_model=return_model, bootstrap_block_months=bootstrap_block_months,
            bootstrap_history_path=bootstrap_history_path,
        )

    required_monthly = search3["required_monthly_contribution"]
    found3 = search3["found"]
    annual_contrib = required_monthly * 12
    total_contrib = t3_init + annual_contrib * t3_years

    if not found3:
        st.warning(f"Could not achieve {t3_prob*100:.0f}% probability even with Rp50M/month. "
                   "Consider lowering the target, increasing the time horizon, or accepting a lower probability.")

    full3 = run_accumulation_simulation(
        initial_portfolio=t3_init, monthly_contribution=required_monthly,
        stock_allocation=stock_allocation,
        stock_return=stock_return, stock_std=stock_std,
        bond_return=bond_return, bond_std=bond_std,
        current_age=t3_current_age, retirement_age=t3_retire_age,
        num_simulations=num_simulations, seed=seed,
        return_model=return_model, bootstrap_block_months=bootstrap_block_months,
        bootstrap_history_path=bootstrap_history_path,
    )

    final3 = full3["final_portfolios"]
    reached3 = final3 >= t3_target
    prob_ok = np.mean(reached3) * 100
    prob_miss = 100 - prob_ok

    st.divider()
    st.subheader("Summary")
    s3_c1, s3_c2, s3_c3, s3_c4 = st.columns(4)
    s3_c1.metric("Initial Savings", fmt_idr(t3_init))
    s3_c2.metric("Target Portfolio", fmt_idr(t3_target))
    s3_c3.metric("Investment Period", f"{t3_years} years (age {t3_current_age} -> {t3_retire_age})")
    s3_c4.metric("Allocation", f"{stock_allocation*100:.0f}% Stocks / {bond_allocation*100:.0f}% Bonds")

    st.divider()
    st.subheader("Primary Results")
    r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
    r3_c1.metric("Required Monthly Contribution", f"Rp{required_monthly / 1e6:.1f}M")
    r3_c2.metric("Actual Probability", fmt_pct(prob_ok))
    r3_c3.metric("Target Probability", fmt_pct(t3_prob * 100))
    r3_c4.metric("Total Contributions", fmt_idr(total_contrib))

    i3_c1, i3_c2, i3_c3 = st.columns(3)
    i3_c1.metric("Annual Contribution", fmt_idr(annual_contrib))
    median3 = np.median(final3)
    i3_c2.metric("Median Portfolio at Retirement", fmt_idr(median3))
    i3_c3.metric("Portfolio Multiple", f"{median3 / total_contrib:.1f}x contributions")

    st.divider()
    st.subheader("Monthly Contribution vs Probability of Reaching Target")
    with st.spinner("Building contribution curve..."):
        curve3 = build_contribution_curve(
            initial_portfolio=t3_init, target_portfolio=t3_target,
            stock_allocation=stock_allocation,
            stock_return=stock_return, stock_std=stock_std,
            bond_return=bond_return, bond_std=bond_std,
            current_age=t3_current_age, retirement_age=t3_retire_age,
            num_points=20, num_simulations=10_000, seed=seed,
            return_model=return_model, bootstrap_block_months=bootstrap_block_months,
            bootstrap_history_path=bootstrap_history_path,
        )
    cdf3 = pd.DataFrame(curve3)

    fig_c3 = go.Figure()
    fig_c3.add_trace(go.Scatter(x=cdf3["contribution"], y=cdf3["success_rate"],
                                mode="lines+markers", name="Probability",
                                line=dict(color="#42a5f5", width=3), marker=dict(size=8)))
    fig_c3.add_hline(y=t3_prob * 100, line_dash="dash", line_color="#ef5350",
                     annotation_text=f"Target: {t3_prob*100:.0f}%", annotation_position="top left")
    fig_c3.add_vline(x=required_monthly, line_dash="dash", line_color="#66bb6a",
                     annotation_text=f"Required: Rp{required_monthly/1e6:.1f}M/mo",
                     annotation_position="top right")
    fig_c3.update_layout(xaxis_title="Monthly Contribution (IDR)",
                         yaxis_title="Probability of Reaching Target (%)",
                         xaxis=dict(tickformat=",.0f"), yaxis=dict(range=[0, 105]),
                         template="plotly_white", height=450, showlegend=False)
    st.plotly_chart(fig_c3, use_container_width=True, key="t3_contrib_curve")

    st.info(f"**Required monthly contribution: Rp{required_monthly/1e6:.1f}M/month** "
            f"for a {t3_prob*100:.0f}% chance of reaching {fmt_idr(t3_target)} in {t3_years} years.")

    st.divider()
    st.subheader("Portfolio at Retirement — Distribution Statistics")
    sc3_1, sc3_2 = st.columns(2)
    with sc3_1:
        st.markdown("**Percentile Distribution**")
        ps3 = {"Mean": fmt_idr(np.mean(final3)), "Median": fmt_idr(np.median(final3)),
               "5th Percentile": fmt_idr(np.percentile(final3, 5)),
               "25th Percentile": fmt_idr(np.percentile(final3, 25)),
               "75th Percentile": fmt_idr(np.percentile(final3, 75)),
               "95th Percentile": fmt_idr(np.percentile(final3, 95))}
        st.dataframe(pd.DataFrame(ps3.items(), columns=["Metric", "Value"]),
                     use_container_width=True, hide_index=True)
    with sc3_2:
        st.markdown("**Target Analysis**")
        ta3 = {"Target Portfolio": fmt_idr(t3_target),
               "Probability of Reaching Target": fmt_pct(prob_ok),
               "Probability of Falling Short": fmt_pct(prob_miss),
               "Median Shortfall / Surplus": fmt_idr(np.median(final3) - t3_target),
               "5th Percentile Outcome": fmt_idr(np.percentile(final3, 5)),
               "95th Percentile Outcome": fmt_idr(np.percentile(final3, 95))}
        st.dataframe(pd.DataFrame(ta3.items(), columns=["Metric", "Value"]),
                     use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Charts")
    st.markdown("#### Simulated Accumulation Paths (sample of 100)")
    fig_p3 = go.Figure()
    idx3 = np.random.choice(num_simulations, size=min(100, num_simulations), replace=False)
    for idx in idx3:
        c3 = "#66bb6a" if reached3[idx] else "#ef5350"
        fig_p3.add_trace(go.Scatter(x=full3["ages"], y=full3["portfolio_paths"][idx], mode="lines",
                                    line=dict(width=0.8, color=c3), opacity=0.15,
                                    showlegend=False, hoverinfo="skip"))
    fig_p3.add_hline(y=t3_target, line_dash="dash", line_color="#ffa726", line_width=2,
                     annotation_text=f"Target: {fmt_idr(t3_target)}", annotation_position="top right")
    fig_p3.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                line=dict(color="#66bb6a", width=2), name="Reached Target"))
    fig_p3.add_trace(go.Scatter(x=[None], y=[None], mode="lines",
                                line=dict(color="#ef5350", width=2), name="Fell Short"))
    fig_p3.update_layout(xaxis_title="Age", yaxis_title="Portfolio Value (IDR)",
                         yaxis=dict(tickformat=",.0f"), template="plotly_white", height=450,
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_p3, use_container_width=True, key="t3_sample_paths")

    st.markdown("#### Portfolio Value at Retirement — Distribution")
    fig_d3 = go.Figure()
    fig_d3.add_trace(go.Histogram(x=final3[reached3], name="Reached Target",
                                  marker_color="#66bb6a", opacity=0.7, nbinsx=60))
    fig_d3.add_trace(go.Histogram(x=final3[~reached3], name="Fell Short",
                                  marker_color="#ef5350", opacity=0.7, nbinsx=60))
    fig_d3.add_vline(x=t3_target, line_dash="dash", line_color="#ffa726", line_width=2,
                     annotation_text=f"Target: {fmt_idr(t3_target)}", annotation_position="top right")
    fig_d3.update_layout(barmode="overlay", xaxis_title="Portfolio Value at Retirement (IDR)",
                         yaxis_title="Frequency", xaxis=dict(tickformat=",.0f"),
                         template="plotly_white", height=400,
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_d3, use_container_width=True, key="t3_ending_dist")

    st.markdown("#### Probability of Reaching Target")
    fig_dn3 = go.Figure(data=[go.Pie(labels=["Reached Target", "Fell Short"],
                                     values=[prob_ok, prob_miss], hole=0.55,
                                     marker=dict(colors=["#66bb6a", "#ef5350"]),
                                     textinfo="label+percent", textfont_size=14)])
    fig_dn3.update_layout(template="plotly_white", height=350, showlegend=True,
                          legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
    st.plotly_chart(fig_dn3, use_container_width=True, key="t3_donut")

    st.markdown("#### Percentile Accumulation Paths")
    pctl3 = [5, 25, 50, 75, 95]
    pctl_vals = {p: np.percentile(full3["portfolio_paths"], p, axis=0) for p in pctl3}
    pctl_colors = {5: "#ef5350", 25: "#ffa726", 50: "#66bb6a", 75: "#42a5f5", 95: "#7e57c2"}

    fig_pc3 = go.Figure()
    for p in pctl3:
        fig_pc3.add_trace(go.Scatter(x=full3["ages"], y=pctl_vals[p], mode="lines",
                                     name=f"{p}th Percentile", line=dict(width=2.5, color=pctl_colors[p])))
    fig_pc3.add_hline(y=t3_target, line_dash="dash", line_color="#ffa726", line_width=2,
                      annotation_text=f"Target: {fmt_idr(t3_target)}", annotation_position="top right")
    fig_pc3.update_layout(xaxis_title="Age", yaxis_title="Portfolio Value (IDR)",
                          yaxis=dict(tickformat=",.0f"), template="plotly_white", height=450,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_pc3, use_container_width=True, key="t3_pctl_paths")

    st.divider()
    st.subheader("Contribution Breakdown")
    ages_range = list(range(t3_current_age, t3_retire_age + 1))
    cum_contrib = [t3_init + annual_contrib * (a - t3_current_age) for a in ages_range]

    fig_bd = make_subplots(specs=[[{"secondary_y": True}]])
    fig_bd.add_trace(go.Scatter(x=ages_range, y=cum_contrib, name="Cumulative Contributions",
                                mode="lines", line=dict(color="#42a5f5", width=2),
                                fill="tozeroy", fillcolor="rgba(66,165,245,0.1)"), secondary_y=False)
    fig_bd.add_trace(go.Scatter(x=full3["ages"], y=pctl_vals[50], name="Median Portfolio Value",
                                mode="lines", line=dict(color="#66bb6a", width=2.5)), secondary_y=True)
    fig_bd.add_trace(go.Scatter(x=full3["ages"], y=pctl_vals[5], name="5th Percentile",
                                mode="lines", line=dict(color="#ef5350", width=1.5, dash="dot")), secondary_y=True)
    fig_bd.add_hline(y=t3_target, line_dash="dash", line_color="#ffa726", line_width=2,
                     annotation_text=f"Target: {fmt_idr(t3_target)}", annotation_position="top right")
    fig_bd.update_layout(template="plotly_white", height=400,
                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_bd.update_yaxes(title_text="Cumulative Contributions (IDR)", tickformat=",.0f", secondary_y=False)
    fig_bd.update_yaxes(title_text="Portfolio Value (IDR)", tickformat=",.0f", secondary_y=True)
    fig_bd.update_xaxes(title_text="Age")
    st.plotly_chart(fig_bd, use_container_width=True, key="t3_breakdown")

    st.divider()
    st.subheader("Risk Metrics")
    worst3 = np.percentile(final3, 5)
    best3 = np.percentile(final3, 95)
    shortfall = np.mean(final3 < t3_target) * 100

    rm3_c1, rm3_c2 = st.columns(2)
    with rm3_c1:
        st.metric("Probability of Reaching Target", fmt_pct(prob_ok))
        st.metric("Median Final Portfolio", fmt_idr(median3))
        st.metric("5th Percentile Outcome", fmt_idr(worst3))
        st.metric("95th Percentile Outcome", fmt_idr(best3))
    with rm3_c2:
        st.metric("Total Contributions", fmt_idr(total_contrib))
        st.metric("Median Investment Gain", fmt_idr(median3 - total_contrib))
        st.metric("Median Portfolio Multiple", f"{median3 / total_contrib:.1f}x")
        st.metric("Shortfall Risk", fmt_pct(shortfall))

    st.divider()
    st.subheader("Sensitivity Analysis")
    st.markdown("See how the **required monthly contribution** changes when one assumption varies.")
    sens3_target = st.selectbox("Variable to Analyze",
                                ["Target Portfolio", "Initial Savings", "Stock Allocation", "Retirement Age", "Current Age"],
                                key="t3_sens")

    if sens3_target == "Target Portfolio":
        pv3 = [v * 1_000_000 for v in range(1000, 51000, 5000)]
        pn3 = "target_portfolio"
        pd3 = [fmt_idr(v) for v in pv3]
    elif sens3_target == "Initial Savings":
        pv3 = [v * 1_000_000 for v in range(0, 105, 10)]
        pn3 = "initial_portfolio"
        pd3 = [f"Rp{v/1e6:.0f}M" for v in pv3]
    elif sens3_target == "Stock Allocation":
        pv3 = [v / 100 for v in range(0, 101, 10)]
        pn3 = "stock_allocation"
        pd3 = [f"{v*100:.0f}%" for v in pv3]
    elif sens3_target == "Retirement Age":
        pv3 = list(range(40, 71, 5))
        pn3 = "retirement_age"
        pd3 = [str(v) for v in pv3]
    else:
        pv3 = list(range(20, 55, 5))
        pn3 = "current_age"
        pd3 = [str(v) for v in pv3]

    with st.spinner(f"Running sensitivity analysis for {sens3_target}..."):
        sr3 = []
        for val in pv3:
            kw = dict(initial_portfolio=t3_init, target_portfolio=t3_target,
                      stock_allocation=stock_allocation,
                      stock_return=stock_return, stock_std=stock_std,
                      bond_return=bond_return, bond_std=bond_std,
                      current_age=t3_current_age, retirement_age=t3_retire_age,
                      target_success_rate=t3_prob, num_simulations=10_000, seed=seed)
            kw[pn3] = val
            ca3 = kw.get("current_age", t3_current_age)
            ra3 = kw.get("retirement_age", t3_retire_age)
            if ra3 <= ca3:
                sr3.append({sens3_target: val, "Required Monthly": None, "Probability": None, "Found": False})
                continue
            res3 = find_required_contribution(**kw)
            sr3.append({sens3_target: val, "Required Monthly": res3["required_monthly_contribution"],
                        "Probability": res3["success_rate"], "Found": res3["found"]})

    s3df = pd.DataFrame(sr3)
    valid3 = s3df.dropna(subset=["Required Monthly"])
    d3 = pd.DataFrame()
    d3["label"] = pd3[:len(valid3)]
    d3["Required Monthly"] = valid3["Required Monthly"].apply(lambda x: f"Rp{x/1e6:.1f}M" if pd.notna(x) else "N/A")
    d3["Probability"] = valid3["Probability"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
    st.dataframe(d3, use_container_width=True, hide_index=True)

    if len(valid3) > 0:
        fig_s3 = go.Figure()
        fig_s3.add_trace(go.Bar(x=d3["label"], y=valid3["Required Monthly"],
                                name="Required Monthly Contribution", marker_color="#42a5f5",
                                text=d3["Required Monthly"], textposition="outside"))
        fig_s3.update_layout(xaxis_title=sens3_target, yaxis_title="Required Monthly Contribution (IDR)",
                             yaxis=dict(tickformat=",.0f"), template="plotly_white",
                             height=450, showlegend=False)
        st.plotly_chart(fig_s3, use_container_width=True, key="t3_sens_chart")

# ─────────────────────────────────────────────────────────────────────────────
# Disclaimer
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Disclaimer")
st.warning("""
**This is a Monte Carlo simulation model, not a prediction of future investment returns.**

The results depend heavily on user-supplied assumptions for expected returns, volatility,
inflation, asset allocation, and retirement horizon. The model does **not** guarantee
retirement sustainability. Do **not** present any particular failure probability as a
guaranteed real-world probability.

**All return and volatility values are model assumptions**, not historically guaranteed
estimates. Actual investment returns will vary and may be significantly different from
the assumed values.
""")
