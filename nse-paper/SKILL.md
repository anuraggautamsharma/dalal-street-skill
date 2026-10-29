---
name: nse-paper
description: >-
  Paper Trader for Indian stocks: fake-money trades checked against real NSE candles. Opens the trade from
  trader-data/plan.json (only if it PASSed), then walks the 5-minute candles since entry to see whether the
  stop or the target hit first (with gap slippage), closes intraday trades at 15:20, applies Groww's
  estimated charges, and keeps a log with wins, losses, net and average R. Use when the user says "paper
  trade this", "open the paper trade", "check my paper trade", "did it hit my stop", "close it", "my paper
  account", "trade log", or "/nse-paper".
argument-hint: "[init | open | check | close | status | log]"
---

# nse-paper

`${CLAUDE_SKILL_DIR}` is this skill's folder. Run from the user's project folder.

```bash
python3 "${CLAUDE_SKILL_DIR}/paper.py" init --cash 100000
python3 "${CLAUDE_SKILL_DIR}/paper.py" open                     # from trader-data/plan.json
python3 "${CLAUDE_SKILL_DIR}/paper.py" open --price 1425.20     # the ask you would really have paid
python3 "${CLAUDE_SKILL_DIR}/paper.py" check                    # stop? target? flat by 15:20?
python3 "${CLAUDE_SKILL_DIR}/paper.py" close --id 2 --price 1440
python3 "${CLAUDE_SKILL_DIR}/paper.py" status
python3 "${CLAUDE_SKILL_DIR}/paper.py" log
```

State: `trader-data/paper.json`. Fake money only; nothing here touches a broker.

## Steps

1. `open` only after `/nse-plan --write` printed PASS. Buying happens at the **ask** (the sellers' price), so use
   `--price` with the ask from the broker app's market depth when the user has it.
2. While the trade is open, `check` it when the user asks, or on a schedule they set up (for example
   `/loop 5m` running `paper.py check` until it closes; stop the loop once it prints CLOSED).
3. When `check` prints CLOSED, show the result. If the user keeps a trading diary (for example
   `paper-trading-diary.md`), add the trade to it (plan, live notes, result, one or two lessons) using the
   printed diary line.
   Grade the plan-following, not the profit: a loss at the planned stop is a well-played trade.
4. `log` shows the record. Under 20 trades says nothing yet about whether a method works.

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
