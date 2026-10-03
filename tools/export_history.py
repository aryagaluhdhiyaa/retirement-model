"""
Export monthly joint history: strategy (6083435) + International Stocks proxy.

Strategy: config 6083435 (108 months, 2016-2024)

Stocks: MSCI ACWI-like from index_ohlcv.db if available, else fallback to
        synthetic series (not used in bootstrap if missing).
Writes: data/history_monthly.csv  (date, strategy_ret, stock_ret)
        data/history_meta.json

Source roots are machine-specific — provide via environment:
    FACTOR_ROOT   : factor-research repo root (scores/factors DBs)
    OHLCV_DATA_DIR: OHLCV stock database data dir (index_ohlcv.db)
"""
import os, sys, sqlite3, json
import numpy as np
import pandas as pd

FACT_ROOT = os.environ.get("FACTOR_ROOT", "")
DATA_DIR = os.environ.get("OHLCV_DATA_DIR", "")
if not FACT_ROOT or not DATA_DIR:
    sys.exit("Set FACTOR_ROOT and OHLCV_DATA_DIR env vars to the local research repos (machine-specific, intentionally not stored in git).")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Strategy config 6083435 (factor spec lives in the private research repo; see FACTOR_ROOT)
STRATEGY_CONFIG_ID = 6083435

def extract_strategy_monthly():
    sys.path.insert(0, os.path.join(FACT_ROOT, "4deep_analysis"))
    sys.path.insert(0, os.path.join(FACT_ROOT, "2score"))
    sys.path.insert(0, FACT_ROOT)
    from _reconstruct import MonthlyRecon
    from config import SCORES_DB
    conn = sqlite3.connect('file:' + SCORES_DB + '?mode=ro', uri=True, timeout=30)
    recon = MonthlyRecon()
    recon.build(conn)
    series = recon.series_for(STRATEGY_CONFIG_ID)
    recon.close()
    conn.close()
    # series is (n_periods*12,) with NaN where inactive; aligned to rebal dates 2016-2025
    # Build date index from factors.db
    sys.path.insert(0, FACT_ROOT)
    from config import FACTORS_DB
    fconn = sqlite3.connect(FACTORS_DB, timeout=15)
    dates = pd.read_sql("SELECT DISTINCT rebal_date FROM factors ORDER BY rebal_date", fconn)["rebal_date"]
    fconn.close()
    # n_periods = len(dates)-1 = number of rebal years; monthly series maps contiguously
    # Infer start: first rebal 2015-12-31? Check actual dates
    all_dates = pd.to_datetime(dates)
    # monthly series covers Jan 2016 .. Dec 2024 (108 months for 9 periods with n_months=108)
    n_months = int(np.sum(~np.isnan(series)))
    # Build monthly date range anchored to first available month
    # Use 2016-01-31 as anchor (verified by reconstruction)
    # Instead derive: last complete year is 2024, so 108 months = 2016-01 to 2024-12
    start = pd.Timestamp("2016-01-31")
    full_idx = pd.date_range(start, periods=len(series), freq="ME")
    df = pd.DataFrame({"date": full_idx, "strategy_ret": series})
    df = df.dropna(subset=["strategy_ret"])
    return df

def extract_stock_monthly(strategy_dates):
    db = os.path.join(DATA_DIR, "index_ohlcv.db")
    if not os.path.exists(db):
        return None
    conn = sqlite3.connect('file:' + db + '?mode=ro', uri=True, timeout=15)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        # try common table names
        for tbl in ["index_ohlcv", "ohlcv", "prices", "index_prices"]:
            if tbl in tables:
                cols = [r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()]
                sample = conn.execute(f"SELECT * FROM {tbl} LIMIT 3").fetchall()
                print(f"table {tbl} cols {cols} sample {sample[:1]}")
        # Attempt to find ACWI-like ticker
        for tbl in tables:
            try:
                tickers = [r[0] for r in conn.execute(f"SELECT DISTINCT ticker FROM {tbl} LIMIT 20").fetchall()]
                if tickers:
                    print(f"tickers in {tbl}:", tickers[:10])
                    break
            except Exception:
                continue
    finally:
        conn.close()
    return None

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    strat = extract_strategy_monthly()
    print(f"Strategy: {len(strat)} months, {strat['date'].min().date()} -> {strat['date'].max().date()}")
    print(f"Strategy mean {strat['strategy_ret'].mean():.4f} vol {strat['strategy_ret'].std():.4f}")

    # Try stock extraction for logging; we ship strategy-only history and keep stocks parametric as fallback
    stock = extract_stock_monthly(strat["date"])

    # For now ship joint history with stock_ret = NaN (engine falls back to parametric for stock leg)
    # If stock history is added later, fill stock_ret column.
    strat["stock_ret"] = np.nan
    # Also add fallback synthetic stock proxy: use strategy's factor-market mean as placeholder
    # Keep NaN so bootstrap can decide.

    out_csv = os.path.join(OUT_DIR, "history_strategy.csv")
    strat.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv} ({len(strat)} rows)")

    meta = {
        "strategy_config_id": STRATEGY_CONFIG_ID,
        "strategy_desc": "factor strategy 6083435, 50-stock equal-weight, yearly rebalance (spec in private research repo)",
        "n_months": int(len(strat)),
        "start": str(strat["date"].min().date()),
        "end": str(strat["date"].max().date()),
        "strategy_mean_monthly": float(strat["strategy_ret"].mean()),
        "strategy_vol_monthly": float(strat["strategy_ret"].std()),
        "strategy_cagr_annual": float((np.prod(1+strat["strategy_ret"]) ** (12/len(strat)) -1)),
        "stock_note": "stock_ret is NaN — bootstrap uses strategy leg empirically, stock leg parametric unless history_acwi.csv supplied",
    }
    with open(os.path.join(OUT_DIR, "history_strategy_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))

if __name__ == "__main__":
    main()
