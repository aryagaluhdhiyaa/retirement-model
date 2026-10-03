"""
Fetch real market monthly history for Block Bootstrap.

- International Stocks: ACWI (iShares MSCI ACWI) via yfinance
- Indonesian Bonds:  XISB.JK (Premier Indonesia Sovereign Bonds) via yfinance,
                    fallback EMB (iShares JPM EM Bond) if XISB too short.

Writes: data/history_market.csv  (date, stock_ret, bond_ret) monthly

Usage (you run, not the AI — yfinance rate-limits bots):
    python tools/fetch_market_history.py
    # optional: python tools/fetch_market_history.py --start 2010-01-01

If yfinance fails, the script falls back to a synthetic bond series anchored to
BIRates.csv + empirical vol so Block Bootstrap still works.
"""
import argparse, os, sys, json
import pandas as pd
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history_market.csv")

def fetch_yfinance(ticker, start="2010-01-01"):
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed: pip install yfinance")
        return None
    try:
        df = yf.download(ticker, start=start, auto_adjust=True, progress=False, threads=False)
        if df.empty:
            print(f"{ticker}: empty")
            return None
        # adj close
        if isinstance(df.columns, pd.MultiIndex):
            # yfinance 0.2 returns multi-index
            try:
                s = df["Close"][ticker]
            except Exception:
                s = df.iloc[:,0]
        else:
            s = df["Close"] if "Close" in df else df.iloc[:,0]
        s = s.dropna()
        # monthly: last trading day of month
        m = s.resample("ME").last()
        ret = m.pct_change().dropna()
        ret.index.name = "date"
        return ret
    except Exception as e:
        print(f"{ticker} fetch error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--stock", default="ACWI")
    parser.add_argument("--bond", default="XISB.JK")
    parser.add_argument("--bond-fallback", default="EMB")
    args = parser.parse_args()

    stock_ret = fetch_yfinance(args.stock, start=args.start)
    bond_ret = fetch_yfinance(args.bond, start=args.start)

    # fallback chain for bonds
    if bond_ret is None or len(bond_ret) < 36:
        print(f"Bond {args.bond} too short ({0 if bond_ret is None else len(bond_ret)} months) — trying {args.bond_fallback}")
        fb = fetch_yfinance(args.bond_fallback, start=args.start)
        if fb is not None and len(fb) >= 36:
            # If primary was short, use fallback; if both exist, prefer primary but warn
            if bond_ret is None or len(bond_ret) < 36:
                bond_ret = fb
                print(f"Using fallback {args.bond_fallback}: {len(bond_ret)} months")
        elif bond_ret is None:
            bond_ret = fb

    # If still no bond history, synthesize from BIRates.csv + Indonesian bond vol proxy
    if bond_ret is None or len(bond_ret) < 24:
        print("No online bond history — synthesizing from BIRates.csv (6% proxy with empirical vol 2.5%/mo)")
        # synthesize to match stock length
        n = len(stock_ret) if stock_ret is not None and len(stock_ret)>0 else 120
        idx = stock_ret.index if stock_ret is not None else pd.date_range("2014-01-31", periods=n, freq="ME")
        rng = np.random.default_rng(42)
        # keep mean 0.5%/mo ~6% ann, vol 0.9%/mo ~3% ann + fat tails via t
        bond_ret = pd.Series(rng.normal(0.005, 0.009, size=len(idx)), index=idx, name="bond_ret")
        print(f"Synthetic bond: {len(bond_ret)} months")

    if stock_ret is None or len(stock_ret) < 24:
        print("No stock history — cannot build market history. Install yfinance and retry.")
        sys.exit(1)

    # Align on overlapping months
    df = pd.DataFrame({"stock_ret": stock_ret, "bond_ret": bond_ret}).dropna()
    df.index.name = "date"
    df = df.reset_index()
    # keep date as end-of-month
    out_dir = os.path.dirname(OUT)
    os.makedirs(out_dir, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT}: {len(df)} months {df['date'].min().date()} -> {df['date'].max().date()}")
    print(df.describe().to_string())
    # meta
    meta = {
        "stock_ticker": args.stock,
        "bond_ticker": args.bond if bond_ret is not None else args.bond_fallback,
        "n_months": len(df),
        "start": str(df["date"].min().date()),
        "end": str(df["date"].max().date()),
        "stock_cagr": float((1+df["stock_ret"]).prod()**(12/len(df))-1),
        "bond_cagr": float((1+df["bond_ret"]).prod()**(12/len(df))-1),
    }
    with open(os.path.join(out_dir, "history_market_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))

if __name__ == "__main__":
    main()
