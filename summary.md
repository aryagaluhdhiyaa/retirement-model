# Retirement Planning — Summary of Findings

Date: 2026-09-25. Status: final-canonical numbers. Superseded figures are logged once at the bottom, not repeated.
Audience: plain-language summary first (§1); technical appendix with file:line citations for a reviewing AI agent (§2+).

---

## 1. TL;DR — the deal in ten lines

1. Save **Rp1M/month from 22→40** (starting from 50M), invested 50% My Strategy / 50% world stocks (VT≈ACWI).
2. Land **~2.5B at 40** (median outcome on realistic strategy assumptions; target line 2.7B).
3. Spend **6M/month in today's money** (8.57M at 40, +2%/yr) from a **70% world stocks / 30% Indonesian SBN** portfolio, 40→85.
4. That planet needs **2.46B at 40 for 70% success** (verified 2026-09-25: 71.2%).
5. **Landing the target at 40 is the most important thing.** Great retirement returns cannot save a short landing (see sim 5097, §5).
6. **Tiny work 40–50 is the cheapest insurance:** +Rp3M/mo × 10y lifts a 2.0B landing 53%→67%, a 1.5B landing 24%→40% (§6).
7. **Don't go 100% stocks in retirement:** 100/0 needs 2.70B vs 2.41B for 70/30 at the same 70% bar — volatility drag + sequence risk (§4).
8. **The 39%-strategy graphs are optimistic.** On live-plausible 25–30% the median landing is 2.44–3.41B and the bad quartile can hit zero (§7).
9. Joint odds reminder: 70% to save × 70% to spend ≈ **49%** to do both.
10. Dashboard (`app_unified.py`) runs DMS Block Bootstrap only; graphs live in `graph/`.

---

## 2. Engine & canonical assumptions

- **Engine:** Block Bootstrap (IS block bootstrap, not plain): circular overlapping **6-month joint monthly blocks** (3/6/12 selectable, 6 default), annualized `∏(1+r_m)−1`. Code: `bootstrap.py`, `simulation.py`. Dashboard is **DMS-only** — the Normal/DMS toggle and return/vol sliders were removed (`app_unified.py` sidebar); Normal survives only as a missing-file fallback.
- **Conventions:** annual rebalance; beginning-of-year withdrawal (conservative); failure = portfolio ≤ 0 at any point; inflation 2% (user-confirmed; BI target 2.5%±1%, BPS 2016–2023 avg 3.12% — 2% is the optimistic end, kept per user + Ben Felix −1% spending-smile reasoning discussed in chat).
- **Seeds:** dashboard default 42; life-path pools seed 7, retirement draw stream 7001, curation sub-seed 777 (`graph/paths_pool.py`).

### Histories (all in `data/`)

| File | Content | Use |
|---|---|---|
| `history_market.csv` | 1488mo 1900–2023. Stocks DMS Global 7.2% nominal; bonds **Indonesian SBN 6.0%** (user-confirmed; BI Rate is a policy-rate level, not a return series, so the long leg is synthetic; vol 11.5% = realized XISB.JK/EMB 222mo). Calibrated to exact 7.20%/6.00% CAGRs. | Retirement leg |
| `history_market_meta.json` | Provenance for the above | — |
| `history_joint_stock_strategy.csv` | 96mo 2016–2023. ACWI 11.24% + strategy 6083435 at 39.23% (corrected). | Accumulation leg (optimistic set) |
| `history_joint_25pct.csv` / `history_joint_30pct.csv` | Same file, strategy leg rescaled to exact 25.00%/30.00% CAGR (shape/crashes preserved; stock leg untouched at 11.24%). | Accumulation leg (honest set) |
| `history_market_etf.csv` | 222mo 2008–2026 real ACWI+XISB/EMB (4.6% bond CAGR, 11.45% vol, corr 0.68). Too short + bull-biased for 45y retirements; sidecar only. | Vol calibration |

Generator: `tools/fetch_study_history.py` (`--bond-mean/--bond-vol`, default 0.06/0.115; 5-iteration CAGR calibration). Regenerating with defaults reproduces the canonical file.

---

## 3. Scenario results (canonical)

Base spend anchor everywhere: 6M today's money → 8.57M/mo at 40 (2%×18y), +2%/yr after. Retirement 40→85 (45y).

### 3a. Spending — 100% world stocks 7.2% (bond-free, so unaffected by the 5%→6% change)

| Spend today | 70% | 50% | 40% | (Normal / DMS Block) |
|---|---|---|---|---|
| 6M (8.57M at 40) | 3.23B / **2.70B** | 2.46B / 2.02B | 2.17B / 1.78B |
| 8M (11.43M at 40) | 4.30B / 3.62B | 3.28B / 2.70B | 2.89B / 2.36B |

### 3b. Spending — 75/25 and 70/30 with 6% SBN (canonical)

- **6M @70%, 75/25 → 2.46B** (verified 2026-09-25, 71.2%). The headline target.
- **100/0 vs 70/30 @70%:** 2.70B vs **2.41B**. Same 2.46B capital: 64.7% vs 72.7% success; median ending 8.76B vs 11.38B; 95th-percentile 214B vs 125B (stocks win only the lottery tail). 20k sims. See §4 for why.
- Retire-30/35/40 × 50/60/70% comparison table from chat was computed on the **superseded 5% bond leg** (†): ordering and ratios stand; absolute DMS needs read ~3–4% high vs the 6% file. Not reproduced here to avoid stale canon.

### 3c. Saving — 22→40, 50M start, 50/50 strategy+stocks, 70% to target

| Target | Normal (40% strategy) | DMS joint (39.2% corrected) |
|---|---|---|
| 3.0B | Rp0.88M (71.9%) | **Rp0.39M (73.3%, verified 2026-09-25)** |
| 3.5B | Rp1.17M (71.7%) | Rp0.59M (72.3%) |
| Strategy at 30% → 3B | Rp2.34M Normal | Rp1.46M DMS (scaled joint file) |

### 3d. Life-path pools (Rp1M/mo, 50M start, seed 7, 20k sims)

| Accumulation leg | Median landing at 40 | P(success to 85) |
|---|---|---|
| 39.2% joint (optimistic) | 6.42B | 94.5% |
| 30% haircut | 3.41B | 80.8% |
| 25% haircut | 2.44B (below 2.7B line) | 64.8% |

### 3e. House goal (separate; 100% stocks, bond-free, still valid)

1.5B house, save 25→40 (15y), 75% success: **Rp6.35M/mo** from 0 (Rp5.96M from 50M). At 50%: Rp4.79M (Rp4.30M from 50M).

---

## 4. Finding: bonds beat 100% stocks at the 70% bar (sequence risk + volatility drag)

- **Volatility drag:** geometric ≈ arithmetic − σ²/2. 100/0: 7.2−1.45 ≈ **5.75%**; 70/30: 6.84−0.81 ≈ **6.03%**. The bond sleeve lowers the average but raises compounded growth — 70/30 wins even the median ending.
- **Sequence signature (measured):** failed paths sat at **0.76× (100/0) / 0.82× (70/30)** of start within years 1–5 vs 0.98–0.99× for survivors; median failure age 66 vs 69; 75–89% of failures occur after 60 — a slow bleed from an early wound, not a year-2 crash.

---

## 5. Finding: sim 5097 — landing is destiny (P25@25% pool)

Sim 5097 (P25 of the 25% pool): landed **0.62B** (bottom 8 of 20,000, 0.04th percentile) with a **16.6%/yr withdrawal rate** at 40 — dead on arrival. Its retirement returns were **top-5%**: first-5y +19.3%/yr (94.9th pct), 45y CAGR 10.95% (95.4th pct) — and it still broke ~50. Not sequence risk; **undercapitalization**. Pool context: 35.2% fail (≈1-in-2.8); all 8 sims landing ≤0.62B failed; all 53 landing within ±25% of it failed.

---

## 6. Finding: barista backstop (70/30 DMS, 8.57M spend, flat nominal top-up income)

| Landing | No work | +Rp3M×10y | +Rp5M×10y | +Rp3M×5y |
|---|---|---|---|---|
| 1.50B | 24% | 40% | 51% | 34% |
| 2.00B | 53% | 67% | 74% | 61% |
| 2.46B | 73% | 81% | 86% | 78% |

Works twice: cuts the withdrawal rate when the portfolio is most fragile, and covers the first decade — the exact window where failures are conceived (§4). Worth most when the landing is short.

---

## 7. Graph gallery (`graph/`)

Optimistic set (39.2% joint leg) vs honest set (25%/30% haircuts). All linear nominal IDR, 2.7B reference line, age-40 marker, seeds 7/7001/777.

| File | Content | Key reading |
|---|---|---|
| `5_random_path.png` | Median + 2 survivors (blue), 2 failures (red flat @61/@72) | Failures incl. one that landed *above* target (3.92B) — sequence kills too |
| `median_path.png` | Median survivor sim 12766: 12.17B → 108.97B | What-good-looks-like; NOT the plan (lucky landing, §8 of chat) |
| `p25_path.png` | P25 sim 7684: 8.52B → 35.26B (survives) | Bad-but-plausible still 13× target |
| `median_haircut_25_30.png` | Median@25% (3.90B→30.42B, orange) + median@30% (2.17B→47.75B, blue) | Lower landing, higher ending — draw beats landing |
| `p25_haircut_25_30.png` | P25@25% FAILS (0.62B→0, broke ~50) vs P25@30% survives (2.84B→4.67B) | 5pts of strategy CAGR = ruin vs comfort in the bad quartile |
| `paths5_haircut_25_30.png` | Same two medians, comparison framing | Head-to-head without arrow clutter |

Code: `graph/paths_pool.py` (shared pool; `build_pool(joint_path=...)`), `graph/plot_{5_paths,median_path,p25_path,haircut_25_30}.py`. Run from repo root, e.g. `python graph/plot_median_path.py`.

---

## 8. Repro commands (repo root, `.venv` active)

```
streamlit run app_unified.py
.\.venv\Scripts\python tools\fetch_study_history.py            # regenerates history_market.csv (6% SBN default)
.\.venv\Scripts\python tools\fetch_study_history.py --bond-mean 0.065
.\.venv\Scripts\python graph\plot_5_paths.py                   # 5_random_path.png
.\.venv\Scripts\python graph\plot_median_path.py               # median_path.png
.\.venv\Scripts\python graph\plot_p25_path.py                  # p25_path.png
.\.venv\Scripts\python graph\plot_haircut_25_30.py             # 3 honest-set PNGs
```

Headline re-verification (2026-09-25): spend 6M@70% 75/25 DMS → **2.46B @71.2%**; save 3B@70% DMS joint → **Rp0.39M @73.3%**.

---

## 9. Superseded log (do not use as canon)

- **Indonesian bonds 5% → 6% SBN:** file was hand-patched while the generator still wrote 3.8% World bonds; fixed 2026-09-21 (6% user-confirmed SBN anchor, 11.5% realized XISB vol, CAGR calibration). Old DMS needs (e.g. 2.55B) read ~3–4% high.
- **Normal/DMS toggle + return/vol sliders removed:** sliders were dead inputs under bootstrap (`bootstrap.py` ignores them when history exists); dashboard now DMS-only.
- **Normal-mode headline 2.94B:** smooth-math reference only.
- **Optimistic accumulation (39.2%/6.42B median landing):** kept as graphs for contrast; planning uses 25–30% haircuts.
- Tables in chat computed on the 5% leg († retire-30/35/40) keep their ordering/ratios; absolutes superseded by §3.
