"""
Fetch / synthesize study-based long-run history for Block Bootstrap.

DMS Global (Credit Suisse Yearbook, Dimson-Marsh-Staunton 1900-2023):
  World stocks 5.2% real + 2% inflation = 7.2% nominal, vol 17% ann
  Indonesian SBN bonds: 6.0% nominal (user-confirmed SBN anchor; BI Rate is a
  policy-rate level, not a return series, so the long-run leg is synthetic —
  see note below), vol 11.5% ann = realized XISB.JK/EMB 222mo monthly vol,
  corr ~0.1 (long-run assumption; the 222mo window shows 0.68, crisis-biased).
  123 years = 1488 months. Uses t(df=6/8) fat tails + 4% joint crash months
  to replicate real crash clustering (1929, 1973, 2008) vs Normal thin tails.

Writes: data/history_market.csv (date, stock_ret, bond_ret) monthly
        data/history_market_meta.json
Keeps:  data/history_market_etf.csv (real ACWI+XISB/EMB 222mo) as side-by-side
"""
import os, json
import numpy as np
import pandas as pd
from scipy.stats import t

OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history_market.csv")

def build_dms(start="1900-01-31", end="2023-12-31",
                stock_ann=0.072, stock_ann_vol=0.17,
                bond_ann=0.06, bond_ann_vol=0.115):
    dates = pd.date_range(start, end, freq="ME")
    n = len(dates)
    rng = np.random.default_rng(42)
    df_s, df_b = 6, 8
    # nominal monthly params
    # bond_ann=0.06: user-confirmed Indonesian SBN anchor (was 0.038 World bonds)
    # bond_ann_vol=0.115: realized XISB.JK/EMB 222mo (2008-2026) monthly vol
    stock_m, bond_m = stock_ann, bond_ann
    # monthly mean via geometric approx: (1+ann)^(1/12)-1
    stock_mean_m = (1+stock_m)**(1/12)-1
    bond_mean_m = (1+bond_m)**(1/12)-1
    stock_vol_m = stock_ann_vol / np.sqrt(12)
    bond_vol_m = bond_ann_vol / np.sqrt(12)
    stock_scale = stock_vol_m * np.sqrt((df_s-2)/df_s)
    bond_scale = bond_vol_m * np.sqrt((df_b-2)/df_b)
    stock_ret = t.rvs(df=df_s, size=n, random_state=42) * stock_scale + stock_mean_m
    bond_ret = t.rvs(df=df_b, size=n, random_state=43) * bond_scale + bond_mean_m
    # correlation ~0.1 via blending
    bond_ret = 0.1*stock_ret + 0.9*bond_ret
    # joint crashes 4% of months (war/crisis)
    crash_idx = rng.choice(n, size=int(n*0.04), replace=False)
    stock_ret[crash_idx] -= rng.uniform(0.06, 0.18, size=len(crash_idx))
    bond_ret[crash_idx] -= rng.uniform(0.01, 0.04, size=len(crash_idx))
    # cap insane single months (keep fat tails but remove >50%)
    stock_ret = np.clip(stock_ret, -0.4, 0.4)
    bond_ret = np.clip(bond_ret, -0.15, 0.15)
    # calibrate to target CAGRs: crash subtractions + vol drag pull the geometric
    # mean below the nominal target, so shift each leg additively (preserves
    # vol, corr and crash alignment — a constant shift changes neither).
    n_months = n
    for _ in range(5):
        for target_ann, series in ((stock_ann, stock_ret), (bond_ann, bond_ret)):
            realized = float((1 + series).prod() ** (12 / n_months) - 1)
            delta_m = (1 + target_ann) ** (1 / 12) - (1 + realized) ** (1 / 12)
            series += delta_m
    stock_ret = np.clip(stock_ret, -0.4, 0.41)
    bond_ret = np.clip(bond_ret, -0.15, 0.16)
    df = pd.DataFrame({"date": dates, "stock_ret": stock_ret, "bond_ret": bond_ret})
    return df

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bond-mean", type=float, default=0.06,
                        help="Bond leg nominal annual mean (default 0.06 = SBN anchor)")
    parser.add_argument("--bond-vol", type=float, default=0.115,
                        help="Bond leg annual vol (default 0.115 = realized XISB.JK/EMB 222mo)")
    parser.add_argument("--stock-mean", type=float, default=0.072)
    parser.add_argument("--stock-vol", type=float, default=0.17)
    args = parser.parse_args()
    df = build_dms(stock_ann=args.stock_mean, stock_ann_vol=args.stock_vol,
                   bond_ann=args.bond_mean, bond_ann_vol=args.bond_vol)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False)
    meta = {
        "source": "DMS Global (Credit Suisse Yearbook 1900-2023) synthetic, SBN-anchored bond leg",
        "stock_nominal": args.stock_mean, "bond_nominal": args.bond_mean,
        "stock_vol_ann": args.stock_vol, "bond_vol_ann": args.bond_vol,
        "n_months": len(df),
        "start": str(df["date"].min().date()),
        "end": str(df["date"].max().date()),
        "stock_cagr": float((1+df["stock_ret"]).prod()**(12/len(df))-1),
        "bond_cagr": float((1+df["bond_ret"]).prod()**(12/len(df))-1),
        "bond_ticker": "Indonesian SBN (synthetic 6% + realized XISB.JK/EMB vol, DMS stock 7.2%)",
        "note": "123y t-fat tails df6/8, 4% joint crashes, corr 0.1 — avoids US exceptionalism (US 6.5% real) and recent valuation-driven bull (ACWI 12.7% 2017-2026). Bond leg 6% = user-confirmed SBN anchor (BI Rate is a policy-rate level, not a return series). ETF 222mo saved as history_market_etf.csv"
    }
    with open(os.path.join(os.path.dirname(OUT), "history_market_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote {OUT}: {len(df)} months {meta['start']} -> {meta['end']}")
    print(df.describe().to_string())
    print(json.dumps(meta, indent=2))

if __name__ == "__main__":
    main()
