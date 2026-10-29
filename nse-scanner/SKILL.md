---
name: nse-scanner
description: >-
  Chart Scanner for Indian stocks. Scans the Nifty 50, Nifty 100, Nifty 500 or a watchlist for simple
  setups: opening-range breakouts and breakdowns (first 5-minute close outside the 9:15-9:30 box), gap ups
  and gap downs (holding, fading or filled), and end-of-day setups (20-day high breakouts, RSI oversold,
  volume spikes, near 20-day lows). Use when the user says "scan the market", "which stocks are breaking
  out", "find setups", "gap ups today", "what moved", "scan nifty", or "/nse-scanner".
argument-hint: "[orb | gaps | daily] [--list nifty50|nifty500|SYMBOLS]"
---

# nse-scanner

`${CLAUDE_SKILL_DIR}` is this skill's folder. Run from the user's project folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb                       # Nifty 50, candles so far
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --list nifty500 --at 10:15
python3 "${CLAUDE_SKILL_DIR}/scan.py" gaps --min-gap 1.5
python3 "${CLAUDE_SKILL_DIR}/scan.py" daily                     # after 3:30 PM, ideas for tomorrow
python3 "${CLAUDE_SKILL_DIR}/scan.py" orb --list JPL,RELIANCE,TCS
```

`--list` takes nifty50 (default), nifty100, nifty500 (NSE's official lists, cached a day), a comma list,
or a file with one symbol per line. Writes `trader-data/scan.json`. Nifty 500 takes a minute or two.

## When to run what

| time (India) | mode |
| --- | --- |
| before 9:15 | `daily` (yesterday's closes) |
| 9:15 to 9:30 | nothing: the opening range is still forming. Wait. |
| from 9:30 | `orb`, `gaps` |
| after 15:30 | `daily` for tomorrow's watchlist |

## Steps

1. Pick the mode from the time, run it, and show the top few rows as printed.
2. Explain one row in kid words (the box, the breakout candle, "busy" volume, holding vs fell back).
3. A scan finds candidates, not trades. Never call a row a buy. Offer `/nse-chart` on the one the user
   picks, then `/nse-plan`. Breakdowns are shown for learning; this pack does not short.

## Safety (every Dalal Street skill)

- **Education and paper trading only.** Nothing in this pack can place an order. Real orders are placed
  by the user, by hand, in their own broker app (Groww, Zerodha, Upstox, Angel One...). Never click
  Buy/Sell in a broker app for them.
- Not SEBI-registered advice: this pack and Claude are not a SEBI-registered Investment Adviser or
  Research Analyst, and are not affiliated with SEBI, RBI, NSE, BSE or any broker.
- Never ask for, read, store or repeat passwords, PINs, OTPs or API keys.
- Not financial advice. Never tell the user to buy, sell or hold a real holding. A PASS is a rules check,
  not a recommendation. Say so once when it matters, plainly.
- Every number comes from the scripts. Never invent a price, an odds figure or a charge.
- Free Yahoo data is unofficial: 5-minute candles, can lag and differ a little from the broker's prices.
  Check the broker app before acting on anything.
- The user is a beginner: explain each result like a patient teacher talking to a 12-year-old, with one
  short real-life comparison when it helps, and define any trading word the first time it appears.
- Long only (buy first, sell later). No F&O, margin (MTF) or short selling unless the user asks to learn
  about it, and even then only as an explanation.
