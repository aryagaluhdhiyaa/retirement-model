# Your Retirement Plan — Simple Version

**No finance jargon. Just what you need to do.**

---

## What you asked
- **Save:** Age `22 → 40` (18 years), `50M` already saved, `50%` My Strategy + `50%` International Stocks, want `70%` chance to succeed
- **Spend:** Age `40 → 85` (45 years), `75%` International Stocks + `25%` Indonesian Bonds, want `70%` chance to succeed, spend `6M/month` today → `8.57M/month` at 40 (2% inflation x 18 years)
- **Together:** `70% × 70% = ~49%` chance both happen

---

## What "Block Bootstrap DMS" means (in one sentence)
The dashboard only runs **Block Bootstrap DMS** now (no Normal toggle): we replay **1900-2023 (123 years)** — wars, crashes, bulls — in 6-month chunks (`data/history_market.csv:1488`). It keeps real fat tails and bad years clustering together. Fixed assumptions: `7.2%` Stocks (`DMS World 5.2% + 2% inflation`) and `6%` Indonesian SBN bonds (your confirmed SBN anchor; BI Rate is a policy rate, not a return — see `history_market_meta.json`).

Your My Strategy `40%` is the **uncorrected** backtest. Corrected after removing dead companies it is `39.2%` (`data/history_joint_stock_strategy.csv:96`, `6083435`), so we show both.

---

## The answer

### 1. How much do you need at 40 to spend 6M?
Think: `8.57M × 12 months × 45 years = 4.6B` just to pay rent, before market help.

- **DMS Block (`7.2%` stocks / `6%` SBN, verified 2026-09-21): `2.46B`** (was `2.55B` on the old `5%` bond leg)

**Take `~2.5B` as your target.** We use `2.46B` below.

### 2. How much to save each month to reach 2.46B by 40?
- **Block Joint history (`39.2%` corrected `6083435` + ACWI): `~Rp 0.2-0.4M / month`**
  (verified `Rp0.39M` for `3B`; scales down slightly for `2.46B`)

All at `70%` chance. The dashboard's save tab now runs DMS-only too.

---

## So what's a good plan?

> **Save `~Rp0.4M/month` for 18 years → you'll have `~2.5B` 7 out of 10 times → that `2.5B` lets you spend `6M` (`8.57M` at 40) for 45 years 7 out of 10 times.**

Together that's about **5 out of 10** to do both. Want higher odds? Save a bit more (`Rp1M`), spend `5M`, or work to `45` (then `Rp0.49M` is enough for `2.75B`).

---

## Why 7% vs 65% confused you before
Old file used `2017-2026` bull (`ACWI 12.77%`) for stocks → `65%` success on `2.5B`. Now with `123y` real history, `7.2%` stocks and `6%` SBN bonds, it's `~2.5B` — fair and not valuation-driven.

---

## Files behind this
- `app_unified.py` sidebar: DMS Block Bootstrap only (`7.2%` stocks / `6%` SBN, dataset card computed live from the CSV)
- `data/history_market.csv:1488` + `data/history_joint_stock_strategy.csv:96` (strategy leg ~39% joint with ACWI)
- `simulation.py:374` (save) / `simulation.py:54` (spend)
