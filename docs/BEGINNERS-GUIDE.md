# Beginner's Guide 🧒📈

*The stock market explained like you're 12, so the skills make sense.*

> This guide is for learning. It isn't advice, and nobody here is a SEBI-registered adviser.
> See the [Disclaimer](../DISCLAIMER.md).

## 1. What is a share?

Imagine your friend runs a lemonade stand and splits it into 100 equal pieces. If you buy 1 piece, you
own **1% of the stand**. That piece is a **share**. When the stand earns more, people want your piece more,
and its price goes up. When it struggles, the price goes down. Sometimes the stand shares its profit with
owners: that's a **dividend**.

## 2. Where are shares traded?

Think of a giant mandi, except people trade shares instead of vegetables.

| Player | Mandi version | Real name |
| --- | --- | --- |
| 🏟️ The market | The mandi | **NSE** and **BSE** (the stock exchanges) |
| 🧑‍💼 Your helper | A shopkeeper with an entry pass | Your **broker** (Groww, Zerodha, Upstox...) |
| 🔐 Your locker | Your bag | Your **demat account** |
| 👮 The referee | Market police | **SEBI** |

Buy today, and the share lands in your demat account the next working day (**T+1**). The market is open
**9:15 AM to 3:30 PM, Monday to Friday** (except holidays).

## 3. Who decides the price?

Nobody alone. It's a never-ending auction.

| Word | Kid meaning |
| --- | --- |
| **Bid** | The price a buyer is offering ("I'll pay ₹99") |
| **Ask** | The price a seller wants ("I'll sell for ₹100") |
| **Spread** | The gap between the best bid and the best ask |
| **LTP** | Last Traded Price, the last deal that actually happened |

To buy **right now**, you pay the **ask**. To sell right now, you get the **bid**.

## 4. Market order vs limit order

- **Market order:** "Buy now at whatever the price is." It happens for sure, but the price can surprise you.
- **Limit order:** "Buy only at ₹X or cheaper." The price is protected, but it may never happen.

## 5. Candles 🕯️

Each candle is one slice of time (on these skills, **5 minutes**):

```
   │   ← wick: the highest price in those 5 minutes
  ┌┴┐
  │ │  ← body: from the open to the close
  └┬┘     green = closed higher than it opened, red = closed lower
   │   ← wick: the lowest price
```

A **long lower wick** means sellers pushed it down, but buyers pushed it back up.

## 6. Floors and ceilings

- **Floor (support):** a price where buyers stopped the fall before.
- **Ceiling (resistance):** a price where sellers stopped the rise before.
- More **touches** means more people are watching that line. But a floor is **not a promise**: it can break.

`/nse-chart` finds these for you.

## 7. The opening range and VWAP

- **Opening range:** the high and low of the first 15 minutes (9:15–9:30). It's a "box". A candle
  closing above the box is a **breakout**.
- **VWAP:** the day's average price, weighted by how many shares traded. Price above VWAP means buyers
  are winning today; below means sellers are.

## 8. Stop-loss: the sleeping guard 💂

You tell a guard: "If the price falls to ₹90, sell immediately." He sleeps until ₹90, then acts.
That's a **stop-loss**. Put it **a little below a floor**, never exactly on it, and **never move it lower**
once you're in a trade. In a fast crash, a real stop can fill a bit worse than its price (**slippage**).

## 9. The 1% rule and R

- Never lose more than **1% of your money** on one trade. With ₹1,00,000, that's ₹1,000.
- **Shares to buy = ₹1,000 ÷ (entry − stop).** With entry ₹1,425 and stop ₹1,410 (₹15 risk): 66 shares.
- **R** is your risk. A target worth 2× the risk is a **2R** target. With 2R targets you can lose more often
  than you win and still be fine: you only need to win about **1 trade in 3** to break even (before charges).

`/nse-plan` does all of this for you, and adds the charges.

## 10. Charges

Every trade pays brokerage, STT, exchange fees, SEBI fees, stamp duty and GST. On a ₹94,000 intraday
round trip, that's about **₹80**. It sounds small, but it adds up fast if you trade a lot.

## 11. Intraday vs delivery

| | Intraday | Delivery |
| --- | --- | --- |
| Hold | Same day, closed by 3:20 PM | Days, months, years |
| Shares come to your demat? | No | Yes |
| Charges | Lower STT | Higher STT + DP charge on selling |

## 12. Your first month

1. **Weeks 1–4: paper trade only.** Use `/nse-paper`. Write every trade in a diary: the plan, what
   happened, one lesson.
2. **Grade the plan, not the profit.** A loss at the planned stop is a *good* trade. A win after moving
   your stop is a *bad* one.
3. **20+ trades** before judging any method. Let the Time Machine and your log tell you the truth.
4. If you ever trade real money, start with **tiny** amounts you can afford to lose, place the orders
   yourself, and keep following your rules.

## Glossary

| Word | Meaning |
| --- | --- |
| **Gap up / gap down** | Opening well above or below yesterday's close |
| **Volume** | How many shares traded. Big volume = many people care |
| **Breakout** | A close above a ceiling or above the opening box |
| **RSI** | A 0–100 speed meter. Under 30 = fell fast ("oversold"), over 70 = rose fast |
| **Target** | The price where you plan to take profit |
| **Paper trading** | Practising with fake money against real prices |
| **F&O** | Futures & options. Advanced, leveraged, and where most beginners lose. Not covered here |
| **MTF** | Margin trading facility: borrowing to buy more. It multiplies losses too. Not covered here |
| **Circuit** | The daily price limit at which the exchange pauses a stock |
| **T+1** | Trade day plus one working day: when shares or money settle |

Happy learning. Seekho pehle, kamao baad mein. 🙏
