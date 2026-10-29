#!/usr/bin/env python3
"""Chart Scanner: look through many NSE stocks for simple setups.

  scan.py orb                      opening-range breakouts so far today (Nifty 50)
  scan.py orb --list nifty500 --at 10:15
  scan.py gaps --min-gap 1.5       stocks that opened far from yesterday's close
  scan.py daily                    end-of-day setups for tomorrow: 20-day highs,
                                   oversold (RSI under 30), volume spikes, near 20-day lows
  scan.py orb --list JPL,RELIANCE,TCS     your own list (or a file, one symbol per line)

Setups:
  orb    the first 15 minutes (9:15 to 9:30) make a box. A breakout is the
         first 5-minute candle that CLOSES above the box's top. A breakdown
         closes below the bottom (shown for learning; short selling is not
         practised here).
  gaps   open vs yesterday's close; "holding" if the price is still beyond
         the open, "fading" if it has fallen back toward yesterday's close.
  daily  close above the highest high of the 20 days before (breakout),
         RSI(14) under 30 (oversold), volume at least 2x the 20-day average,
         close within 2% of the 20-day low.

Writes trader-data/scan.json. Yahoo data, polite: a few requests at a time.
"""
import argparse
import concurrent.futures as cf
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse-lib"))
import nselib as n  # noqa: E402


def one_orb(sym, at, or_minutes):
    bars, meta = n.chart(sym, rng="1d", interval="5m")
    if at:
        bars = n.upto(bars, at)
    o = n.opening_range(bars, or_minutes)
    if not o:
        return None
    k = max(1, or_minutes // 5)
    after = bars[k:]
    vol_or = sum(b["v"] for b in bars[:k]) / k or 1
    hit = None
    for b in after:
        if b["c"] > o["high"]:
            hit = ("breakout", b)
            break
        if b["c"] < o["low"]:
            hit = ("breakdown", b)
            break
    last = bars[-1]
    prev = meta.get("chartPreviousClose")
    r = {"symbol": n.plain(sym), "price": last["c"], "or_high": o["high"], "or_low": o["low"],
         "change_pct": n.pct(last["c"], prev) if prev else None}
    if not hit:
        r.update(setup="inside", note="still inside the box")
        return r
    kind, b = hit
    edge = o["high"] if kind == "breakout" else o["low"]
    r.update(setup=kind, time=n.hhmm(b["t"] + datetime.timedelta(minutes=5)), trigger_close=b["c"],
             beyond_pct=round(abs(n.pct(b["c"], edge)), 2), vol_x=round(b["v"] / vol_or, 2),
             box_pct=round(n.pct(o["high"], o["low"]), 2),
             holding=(last["c"] > o["high"]) if kind == "breakout" else (last["c"] < o["low"]))
    return r


def one_gap(sym, at, min_gap):
    bars, meta = n.chart(sym, rng="1d", interval="5m")
    if at:
        bars = n.upto(bars, at)
    if not bars:
        return None
    prev = meta.get("chartPreviousClose")
    if not prev:
        return None
    g = n.pct(bars[0]["o"], prev)
    if abs(g) < min_gap:
        return None
    last = bars[-1]["c"]
    up = g > 0
    holding = last >= bars[0]["o"] if up else last <= bars[0]["o"]
    filled = last <= prev if up else last >= prev
    return {"symbol": n.plain(sym), "setup": "gap up" if up else "gap down", "gap_pct": g, "open": bars[0]["o"],
            "prev_close": prev, "price": last, "change_pct": n.pct(last, prev),
            "state": "gap filled (back to yesterday's close)" if filled else "holding" if holding else "fading"}


def one_daily(sym):
    bars, meta = n.chart(sym, rng="3mo", interval="1d")
    if len(bars) < 25:
        return None
    last = bars[-1]
    prior = bars[-21:-1]
    hi20 = max(b["h"] for b in prior)
    lo20 = min(b["l"] for b in prior)
    avgv = sum(b["v"] for b in prior) / 20 or 1
    r14 = n.rsi([b["c"] for b in bars])
    tags = []
    if last["c"] > hi20:
        tags.append("20-day high breakout")
    if r14 is not None and r14 < 30:
        tags.append("oversold (RSI %.0f)" % r14)
    if last["v"] >= 2 * avgv:
        tags.append("volume %.1fx" % (last["v"] / avgv))
    if last["c"] <= lo20 * 1.02:
        tags.append("near 20-day low")
    if not tags:
        return None
    return {"symbol": n.plain(sym), "setup": ", ".join(tags), "price": last["c"], "day": str(last["t"].date()),
            "change_pct": n.pct(last["c"], bars[-2]["c"]), "rsi": r14, "high20": hi20, "low20": lo20}


def run(syms, fn, workers):
    out, errors = [], []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {}
        for s in syms:
            futs[ex.submit(fn, s)] = s
            time.sleep(0.05)
        for f in cf.as_completed(futs):
            try:
                r = f.result()
                if r:
                    out.append(r)
            except n.DataError as e:
                errors.append("%s: %s" % (futs[f], e))
    return out, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["orb", "gaps", "daily"])
    ap.add_argument("--list", default="nifty50", help="nifty50, nifty100, nifty500, a comma list, or a file")
    ap.add_argument("--at", help="only use candles finished by HH:MM today (default: now)")
    ap.add_argument("--now", help='pin the clock, "YYYY-MM-DD HH:MM"')
    ap.add_argument("--or-minutes", type=int, default=15)
    ap.add_argument("--min-gap", type=float, default=1.5)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    try:
        syms = n.universe(a.list)
    except n.DataError as e:
        sys.exit("scan.py: %s" % e)
    now = n.now_ist(a.now)
    at = None
    if a.at:
        h, m = a.at.split(":")
        at = now.replace(hour=int(h), minute=int(m), second=0)
    elif a.now:
        at = now

    if a.mode == "orb":
        rows, errs = run(syms, lambda s: one_orb(s, at, a.or_minutes), a.workers)
        bo = sorted([r for r in rows if r["setup"] == "breakout"], key=lambda r: (-r["vol_x"]))
        bd = sorted([r for r in rows if r["setup"] == "breakdown"], key=lambda r: (-r["vol_x"]))
        inside = [r for r in rows if r["setup"] == "inside"]
        print("Opening-range scan, %s stocks, %d-minute box (9:15 to %s)%s" % (
            len(syms), a.or_minutes, (datetime.datetime(2000, 1, 1, 9, 15) + datetime.timedelta(minutes=a.or_minutes)).strftime("%H:%M"),
            ", candles up to " + a.at if a.at else ""))
        print("%d broke out UP, %d broke DOWN, %d still inside the box.\n" % (len(bo), len(bd), len(inside)))
        if bo:
            print("BREAKOUTS (first close above the box), busiest first:")
            print("  %-12s %-6s %10s %10s %8s %7s %7s  %s" % ("stock", "time", "box top", "close", "beyond", "vol", "box", "now"))
            for r in bo[:a.top]:
                print("  %-12s %-6s %10.2f %10.2f %7.2f%% %6.1fx %6.2f%%  %s %.2f" % (
                    r["symbol"], r["time"], r["or_high"], r["trigger_close"], r["beyond_pct"], r["vol_x"], r["box_pct"],
                    "holding" if r["holding"] else "fell back", r["price"]))
        if bd:
            print("\nBREAKDOWNS (first close below the box):")
            for r in bd[:a.top]:
                print("  %-12s %-6s box bottom %.2f, closed %.2f, %s %.2f" % (
                    r["symbol"], r["time"], r["or_low"], r["trigger_close"], "still below" if r["holding"] else "came back", r["price"]))
        print("\nvol = the breakout candle's volume vs an average opening-range candle. box = how tall the box is.")
        print("A breakout that 'fell back' is a warning: the move did not stick.")
        result = {"mode": "orb", "breakouts": bo, "breakdowns": bd, "inside": len(inside)}
    elif a.mode == "gaps":
        rows, errs = run(syms, lambda s: one_gap(s, at, a.min_gap), a.workers)
        rows.sort(key=lambda r: -abs(r["gap_pct"]))
        print("Gap scan, %s stocks, gaps of %.1f%% or more:\n" % (len(syms), a.min_gap))
        for r in rows[:a.top]:
            print("  %-12s %-8s %+6.2f%%  open %.2f  now %.2f (%+.2f%% on the day)  %s" % (
                r["symbol"], r["setup"], r["gap_pct"], r["open"], r["price"], r["change_pct"], r["state"]))
        if not rows:
            print("  none today")
        result = {"mode": "gaps", "rows": rows}
    else:
        rows, errs = run(syms, one_daily, a.workers)
        rows.sort(key=lambda r: r["symbol"])
        print("Daily scan, %s stocks (daily candles, last close):\n" % len(syms))
        for r in rows[:max(a.top, 40)]:
            print("  %-12s %10.2f  %+6.2f%%  RSI %-5s %s" % (r["symbol"], r["price"], r["change_pct"], r["rsi"], r["setup"]))
        if not rows:
            print("  nothing matched")
        result = {"mode": "daily", "rows": rows}

    if errs:
        print("\n%d stock(s) had no data: %s" % (len(errs), "; ".join(errs[:5]) + (" ..." if len(errs) > 5 else "")))
    print("\nA scan finds candidates, not trades. Next: /nse-chart on one of them, then /nse-plan.")
    result.update(at=a.at or n.hhmm(now), list=a.list, scanned=len(syms), errors=errs)
    n.write_json(n.data_path("scan.json"), result)


if __name__ == "__main__":
    main()
