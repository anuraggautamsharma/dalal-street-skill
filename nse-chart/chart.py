#!/usr/bin/env python3
"""Chart Reader: one NSE/BSE stock's day in plain words.

  chart.py JPL                      today so far (or the last session)
  chart.py RELIANCE --days 5        floors and ceilings from the last 5 sessions
  chart.py JPL --now "2026-10-29 12:10"   as it looked at 12:10
  chart.py JPL --json               machine-readable

Prints the price, the gap, the opening range, VWAP, volume against earlier
days, the floors (support) and ceilings (resistance) with how many times the
price turned there, and the last few candles described one by one.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse-lib"))
import nselib as n  # noqa: E402


def describe(b):
    body = b["c"] - b["o"]
    rng = (b["h"] - b["l"]) or 0.01
    colour = "green" if body > 0 else "red" if body < 0 else "flat"
    upper = b["h"] - max(b["o"], b["c"])
    lower = min(b["o"], b["c"]) - b["l"]
    words = []
    if abs(body) / rng >= 0.7:
        words.append("strong %s body" % colour)
    elif abs(body) / rng <= 0.2:
        words.append("tiny body (buyers and sellers tied)")
    else:
        words.append(colour)
    if lower / rng >= 0.5:
        words.append("long lower wick (buyers pushed it back up)")
    if upper / rng >= 0.5:
        words.append("long upper wick (sellers pushed it back down)")
    return colour, ", ".join(words)


def build(sym, days, now, exchange):
    bars, meta = n.chart(sym, rng="5d" if days <= 5 else "1mo", interval="5m", exchange=exchange)
    if now:
        bars = n.upto(bars, now)
        if not bars:
            raise n.DataError("no finished candles before %s" % now)
    sess = n.sessions(bars)
    day, today = sess[-1]
    prev_day, prev = sess[-2] if len(sess) > 1 else (None, None)
    recent = [b for d, bs in sess[-days:] for b in bs]
    last = today[-1]
    live = now is None and day == n.now_ist().date() and n.market_status(n.now_ist()) == "open"
    official = n.daily_closes(sym, exchange)
    price = last["c"] if (now or live) else n.day_close(meta, day, today, official)
    prev_close = n.day_close(meta, prev_day, prev, official) if prev else meta.get("chartPreviousClose")
    orr = n.opening_range(today)
    vw = n.vwap(today)
    floors, ceilings = n.levels(recent, price)
    named = []
    if prev:
        named += [("yesterday's high", max(b["h"] for b in prev)), ("yesterday's low", min(b["l"] for b in prev)),
                  ("yesterday's close", prev_close)]
    named += [("today's open", today[0]["o"]), ("today's high", max(b["h"] for b in today)),
              ("today's low", min(b["l"] for b in today))]
    vol_today = sum(b["v"] for b in today)
    cut = today[-1]["t"].time()
    earlier = [sum(b["v"] for b in bs if b["t"].time() <= cut) for d, bs in sess[:-1]]
    vol_ratio = round(vol_today / (sum(earlier) / len(earlier)), 2) if len(earlier) >= 3 and sum(earlier) else None
    closes = [b["c"] for b in today[-12:]]
    trend = "up" if closes[-1] > closes[0] * 1.002 else "down" if closes[-1] < closes[0] * 0.998 else "sideways"
    return {
        "symbol": meta["symbol"], "name": meta.get("longName") or meta.get("shortName"), "day": str(day),
        "as_of": n.hhmm(last["t"] + datetime.timedelta(minutes=5)), "live": live,
        "price": round(price, 2), "prev_close": prev_close,
        "change": round(price - prev_close, 2) if prev_close else None,
        "change_pct": n.pct(price, prev_close) if prev_close else None,
        "gap_pct": n.pct(today[0]["o"], prev_close) if prev_close else None,
        "open": today[0]["o"], "high": max(b["h"] for b in today), "low": min(b["l"] for b in today),
        "opening_range": orr, "vwap": vw, "above_vwap": price > vw if vw else None,
        "volume": vol_today, "volume_vs_earlier_days": vol_ratio, "sessions_used": len(sess[-days:]),
        "listed_sessions_seen": len(sess), "trend_last_hour": trend,
        "floors": floors[:4], "ceilings": ceilings[:4],
        "named_levels": [{"name": a, "price": b} for a, b in named if b],
        "last_candles": [dict(time=n.hhmm(b["t"]), o=b["o"], h=b["h"], l=b["l"], c=b["c"], v=b["v"],
                              say=describe(b)[1]) for b in today[-6:]],
    }


def show(r):
    p = r["price"]
    print("%s  %s  (%s, %s)" % (r["symbol"], r["name"] or "", r["day"], "LIVE as of " + r["as_of"] if r["live"] else "candles up to " + r["as_of"]))
    print()
    if r["prev_close"]:
        word = "UP" if r["change"] > 0 else "DOWN" if r["change"] < 0 else "FLAT"
        print("Price %s  %s %s (%+.2f%%) from yesterday's close %s" % (n.rs(p), word, n.rs(abs(r["change"])), r["change_pct"], n.rs(r["prev_close"])))
        g = r["gap_pct"]
        if abs(g) >= 0.5:
            print("Gap: it opened %s at %s, %+.2f%% %s yesterday's close." % ("UP" if g > 0 else "DOWN", n.rs(r["open"]), g, "above" if g > 0 else "below"))
    print("Today: open %s, high %s, low %s" % (n.rs(r["open"]), n.rs(r["high"]), n.rs(r["low"])))
    o = r["opening_range"]
    if o:
        where = "ABOVE the box" if p > o["high"] else "BELOW the box" if p < o["low"] else "inside the box"
        print("Opening range (9:15 to %s): %s to %s. Price is %s." % (o["end"], n.rs(o["low"]), n.rs(o["high"]), where))
    if r["vwap"]:
        print("VWAP (the day's average price, weighted by volume): %s. Price is %s it, so %s are in control today."
              % (n.rs(r["vwap"]), "above" if r["above_vwap"] else "below", "buyers" if r["above_vwap"] else "sellers"))
    if not r["volume_vs_earlier_days"]:
        print("Volume: %s shares (too few earlier days to compare)." % format(r["volume"], ","))
    else:
        v = r["volume_vs_earlier_days"]
        print("Volume: %s shares, %.1fx a normal day by this time%s." % (format(r["volume"], ","), v,
              " (busy)" if v >= 1.5 else " (quiet)" if v <= 0.7 else ""))
    print("Last hour: %s." % r["trend_last_hour"])
    print()
    print("CEILINGS above (where sellers turned it down before):")
    for c in reversed(r["ceilings"][:3]):
        print("   %s   %d touch%s, %+.2f%% away" % (n.rs(c["price"]), c["touches"], "" if c["touches"] == 1 else "es", n.pct(c["price"], p)))
    if not r["ceilings"]:
        print("   none found in the candles used")
    print("-- price now %s --" % n.rs(p))
    for f in r["floors"][:3]:
        print("   %s   %d touch%s, %+.2f%% away" % (n.rs(f["price"]), f["touches"], "" if f["touches"] == 1 else "es", n.pct(f["price"], p)))
    if not r["floors"]:
        print("   none found in the candles used")
    print("FLOORS below (where buyers held it up before)")
    print()
    print("Other levels people watch: " + ", ".join("%s %s" % (x["name"], n.rs(x["price"])) for x in r["named_levels"]))
    print()
    print("Last candles (5 minutes each):")
    for b in r["last_candles"]:
        print("  %s  O %s  H %s  L %s  C %s  vol %s  %s" % (b["time"], b["o"], b["h"], b["l"], b["c"], format(b["v"], ","), b["say"]))
    if r["listed_sessions_seen"] < 5:
        print()
        print("Note: only %d trading day(s) of candles exist for this stock, so the floors and ceilings are thin." % r["listed_sessions_seen"])
    print()
    print("Data: Yahoo Finance, 5-minute candles; it can differ a little from your broker's prices. This is a description, not advice.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbol")
    ap.add_argument("--days", type=int, default=3, help="sessions to find floors and ceilings in (default 3)")
    ap.add_argument("--now", help='pin the clock, "YYYY-MM-DD HH:MM" India time')
    ap.add_argument("--exchange", default="NSE", choices=["NSE", "BSE"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        r = build(a.symbol, max(1, a.days), n.now_ist(a.now) if a.now else None, a.exchange)
    except n.DataError as e:
        sys.exit("chart.py: %s" % e)
    if a.json:
        print(json.dumps(r, indent=2, default=str))
    else:
        show(r)
    n.write_json(n.data_path("chart.json"), r)


if __name__ == "__main__":
    main()
