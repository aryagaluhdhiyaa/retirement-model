# Retirement Monte Carlo Simulation Dashboard

A Streamlit application that simulates whether a retirement portfolio can sustain inflation-adjusted spending throughout retirement using Monte Carlo methods.

## Setup

### 1. Create and activate virtual environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
streamlit run app_unified.py
```

## Simulation Methodology

### How It Works

1. **Starting Portfolio:** The portfolio begins with the user-specified initial cash amount.

2. **Annual Return Generation (Block Bootstrap — the only engine):**
   - **Block Bootstrap (DMS-anchored, SBN bond leg):** IS block bootstrap (not plain i.i.d.). Samples **circular overlapping monthly blocks** (`3/6/12`, default 6) **jointly** from `data/history_market.csv` (`stock_ret` + `bond_ret` monthly, 1488mo 1900–2023). Stocks anchored at DMS Global 7.2% nominal; bonds at **Indonesian SBN 6.0%** (BI Rate is a policy-rate level, not a return series — long-run leg is synthetic, vol 11.5% from realized XISB.JK/EMB; see `tools/fetch_study_history.py`). Preserves fat tails, autocorrelation & cross-asset crashes, then annualized `∏(1+r_m)-1`. If `history_market.csv` is missing, it safely falls back to Normal (i.i.d.). Strategy legs live only in `data/history_joint_*.csv` files used by the `graph/` scripts.

3. **Portfolio Return:** Calculated using the chosen allocation:
   - `Portfolio Return = stock_weight × stock_return + bond_weight × bond_return`

4. **Beginning-of-Year Withdrawal:** Annual spending is withdrawn *before* applying investment returns. This is a more conservative convention because the remaining portfolio faces market risk.

5. **Return Application:**
   - `End-of-Year Value = (Portfolio − Withdrawal) × (1 + Portfolio Return)`

6. **Inflation Adjustment:** Spending increases annually:
   - `Annual Spending(t) = Monthly Spending × 12 × (1 + inflation)^t`

7. **Rebalancing:** Portfolio is rebalanced annually to target allocation.

8. **Repetition:** Steps 2–7 are repeated for the full retirement horizon, then the entire process is repeated thousands of times.

### Failure Definition

A simulation is classified as **FAILED** if the portfolio balance drops to zero or below at any point during the retirement horizon. Once a simulation fails, it remains failed — the portfolio cannot recover.

### Sequence of Returns

The order of returns matters. Each simulation generates a unique sequence of annual returns, and the interaction between return timing and withdrawals can significantly affect outcomes (sequence-of-returns risk).

## Key Assumptions

- **Return model:** Block Bootstrap, DMS-only (Normal is missing-file fallback only). No strategy opt-in in the UI.
- Annual rebalancing to target allocation
- Beginning-of-year withdrawals (conservative convention)
- Constant inflation rate throughout retirement
- No taxes, transaction costs, or other fees
- No additional contributions or windfalls
- Portfolio consists of international stocks and Indonesian bonds / your strategy
- Spending is in Indonesian Rupiah (IDR)

## Model Limitations

- Normal fallback mode: thin tails, no autocorrelation, no cross-asset tail dependence. Strategy window is only 108 months (2016-2024) so unseen extremes are still under-sampled.
- Return assumptions are DMS/SBN-anchored model estimates, not guaranteed historical estimates
- No tax modeling
- No health shock or longevity risk modeling
- Rebalancing is assumed free (no transaction costs)
- Inflation is constant (not stochastic)

## Output

The dashboard provides:

- **Primary Results:** Failure count, failure rate, success rate, initial withdrawal rate
- **Portfolio Statistics:** Mean, median, and percentile ending portfolios
- **Interactive Charts:** Portfolio paths, ending distribution, success/failure donut, percentile paths, spending schedule
- **Risk Metrics:** Failure probability, median ending portfolio, total withdrawals
- **Sensitivity Analysis:** How failure rate changes with one variable while others are held fixed

## Project Structure

```
project/
├── app_unified.py        # Unified dashboard (3 tabs)
├── simulation.py         # Monte Carlo engine (normal + block bootstrap)
├── bootstrap.py          # Block bootstrap (monthly joint blocks → annual)
├── data/
│   ├── history_market.csv     # DMS-anchored market history (stock_ret + bond_ret) for bootstrap
│   ├── history_joint_*.csv   # Accumulation-leg histories (regenerate locally; see graph/ + tools/export_history.py)
├── tools/export_history.py  # Export strategy history from the private factor-research repo (see FACTOR_ROOT)
├── requirements.txt
└── README.md
```

## Dashboards

The unified dashboard (`app_unified.py`) contains three tabs:

| Tab | Question | Description |
|-----|----------|-------------|
| Will My Money Last? | Given portfolio + spending, what's the failure rate? | Decumulation simulation with sensitivity analysis |
| How Much Do I Need? | What portfolio sustains my lifestyle at X% success? | Binary search for minimum required portfolio |
| How Much Should I Save? | What monthly contribution hits my target? | Binary search for required monthly savings |
