---
name: nse-news
description: >-
  News Check for Indian stocks. Recent headlines for one or more NSE/BSE stocks from Yahoo Finance, in
  India time, tagged by the kinds of news that move prices (results, dividend/bonus/split, orders, deals,
  regulator/SEBI, ratings and targets, block deals, listing, management), plus the day's move. Use when the
  user says "any news on Jio", "why did it move", "check the news", "headlines", or "/nse-news", and before
  taking a planned trade.
  Hindi/Hinglish too: "Jio ki news batao", "kyun gira", "khabar kya hai", "खबर बताओ".
argument-hint: "[SYMBOL or SYMBOL,SYMBOL] [--hours 48]"
---

# nse-news

`${CLAUDE_SKILL_DIR}` is this skill's folder. Run from the user's project folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py" JPL
python3 "${CLAUDE_SKILL_DIR}/news.py" JPL,RELIANCE --hours 12
python3 "${CLAUDE_SKILL_DIR}/news.py" --from-plan
```

Writes `trader-data/news.json`. Yahoo's India coverage can be thin: official filings are on
nseindia.com → Corporate Announcements (the user can open it; the site blocks scripts).

## Steps

1. Run it and list the headlines as printed, newest first, with their tags.
2. Explain why a tag matters in one line (results day = big surprise moves; a block deal = a big holder
   selling or buying).
3. Headlines are reported as headlines, never as reasons to buy or sell. A planned trade on a big news day
   deserves extra caution: many traders just stay out.

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

