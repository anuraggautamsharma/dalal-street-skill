# Changelog

## v1.0.0 (29 October 2026)

First public release.

### Skills
- **nse-chart**: chart reader: gap, 9:15–9:30 opening range, VWAP, volume vs normal, floors and ceilings
  with touch counts, the last candles in plain words. Uses NSE's official closing prices.
- **nse-scanner**: Nifty 50 / 100 / 500 or watchlist scans: opening-range breakouts and breakdowns, gaps
  (holding, fading, filled), daily setups (20-day highs, RSI oversold, volume spikes, near 20-day lows).
- **nse-news**: headlines in IST, tagged by type (results, dividend, orders, deals, SEBI/RBI, ratings, block
  deals, listing, management), with the day's move.
- **nse-plan**: entry / stop / target, share count from the 1% rule, estimated Indian charges (brokerage,
  STT, exchange fee, SEBI fee, stamp duty, GST, DP), and PASS / WARN / BLOCK checks against your rules.
- **nse-timemachine**: 10,000 replays of the rest of the day from 60 days of the stock's own 5-minute
  candles, plus the same rule on every real past day, with a break-even-aware verdict.
- **nse-paper**: fake-money trades checked candle by candle (stop first, gap slippage, 15:20 exit), with a
  scorecard.

### Also
- Works on **NSE and BSE**, in IST, in rupees. No API key, standard-library Python 3.9+.
- **Hindi, Hinglish and English** replies (`"language"` setting), Hindi guide and glossary.
- Never places orders, never asks for credentials, no tips. Not SEBI-registered advice.
- Offline test suite on GitHub Actions (Python 3.9, 3.11, 3.13).
