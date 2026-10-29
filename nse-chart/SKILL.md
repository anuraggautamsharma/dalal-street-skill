---
name: nse-chart
description: >-
  Chart Reader for Indian stocks (NSE/BSE). Reads one stock's 5-minute candles and explains the day in
  plain words: price vs yesterday's official close, the gap, the 9:15-9:30 opening range, VWAP, volume vs
  normal, floors (support) and ceilings (resistance) with how many times price turned there, and the last
  six candles described one by one. Use when the user says "read the chart", "how is Jio doing", "where is
  support", "floors and ceilings", "what are the candles saying", "/nse-chart JPL", or names an NSE stock
  and asks about its price action.
  Hindi/Hinglish too: "chart samjhao", "Jio ka chart dikhao", "support kahan hai", "चार्ट समझाओ".
argument-hint: "[SYMBOL, e.g. JPL or RELIANCE]"
---

# nse-chart

`${CLAUDE_SKILL_DIR}` is this skill's folder. Run commands from the user's project folder (where
`trader-data/` lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/chart.py" JPL                          # today (or the last session)
python3 "${CLAUDE_SKILL_DIR}/chart.py" RELIANCE --days 5            # levels from 5 sessions
python3 "${CLAUDE_SKILL_DIR}/chart.py" JPL --now "2026-10-29 12:10" # as it looked at 12:10
python3 "${CLAUDE_SKILL_DIR}/chart.py" JPL --exchange BSE --json
```

Symbols are NSE symbols as broker apps show them (JPL, RELIANCE, TCS, HDFCBANK). "JIO" maps to JPL; NIFTY,
BANKNIFTY and SENSEX map to the indices. Writes `trader-data/chart.json`.

## Steps

1. Run `chart.py` for the stock. If the user is watching their broker's chart, say which numbers they can find
   there (open/high/low, previous close).
2. Explain in this order, briefly: where the price is vs yesterday, the gap, the opening-range box, VWAP
   (who is in control), volume (busy or quiet), the nearest floor and ceiling and how many touches, and
   what the last candles say.
3. Floors and ceilings are where price turned before, not promises. More touches = more people watching.
   If the script notes thin history (a new listing), say so.
4. If the user wants to draw these on their broker's chart (Groww, Kite, TradingView...), offer the exact prices for horizontal lines.
5. If they are thinking about a trade, the next step is `/nse-plan`.

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

## Language: Hindi, Hinglish or English

- Reply in the language the user writes in. Hindi in Devanagari → Hindi; Hindi in Roman letters
  ("Jio ka chart samjhao") → Hinglish; English → English. If `trader-data/config.json` has
  `"language": "hi"`, `"hinglish"` or `"en"`, use that instead.
- The scripts print English. Translate their output into the user's language when explaining, but keep
  the numbers, prices, stock symbols, times and the verdict word (PASS / BLOCK) exactly as printed.
- Keep standard market words in English inside Hindi sentences, with a short meaning the first time:
  "stop-loss (नुकसान रोकने वाला ऑर्डर)", "support यानी floor (जहाँ खरीदार कीमत को गिरने से रोकते हैं)".
- Use Indian number style: ₹1,00,000 (एक लाख), ₹12,34,567.
- Simple, warm teacher tone, like explaining to a 12-year-old. Same safety rules in every language:
  no tips, no "buy this", not SEBI-registered advice (SEBI-पंजीकृत सलाह नहीं).

