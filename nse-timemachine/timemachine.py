#!/usr/bin/env python3
"""Time Machine: replay the rest of the day 10,000 times before you risk a rupee.

  timemachine.py run                         uses trader-data/plan.json
  timemachine.py run --write                 also saves trader-data/timemachine.json
  timemachine.py run --symbol TITAN --entry 4390.30 --stop 4361.85 --target 4447.20 \
                     --entry-time 10:15 --setup orb --stop-rule or-mid
  timemachine.py run --replays 20000 --seed 7 --until 15:20

How it works (adapted from the Day Trader skill's Time Machine for NSE hours):
 1. The pool: full past sessions (at least 70 of the 75 five-minute candles,
    9:15 to 15:25 India time; Yahoo skips a few), from the last 60 days, before the plan's day. Every
    candle becomes four ratios to the candle before it: open, high, low and
    close over the previous close.
 2. One replay: start at the entry price at the entry time. For each candle
    left until --until (default the plan's flat-by, 15:20), pick a past
    candle from the same time of day (plus or minus 2 candles) at random and
    scale it to the current price. Check the stop first, then the target; a
    candle touching both counts as the stop.
 3. 10,000 replays give: target first, stop first, neither (still open at
    --until), and the price at --until. R is +target_R at the target, -1 at
    the stop, otherwise (price - entry) / risk.
 4. History: the plan's rule re-run on every one of those real past days.
    setup orb: first 5-minute close above the 9:15-9:30 box (by 14:30), the
    same stop rule and the same reward:risk. Any other setup: buy at the
    entry time every day, with the same stop and target distances in %.
 5. Verdict: of the replays that hit a side, a target R needs to come first
    1 in (1 + R) times to break even (50% at 1R, 33% at 2R). Within 5 points
    of that: close to break-even. 5 to 15: leans. 15+: strongly.

It refuses with fewer than 20 full sessions (a stock that just listed).
A simulation from 60 days of the stock's own candles, not a prediction.
"""
import argparse
import datetime
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse-lib"))
import nselib as n  # noqa: E402

SLOTS = 75          # 9:15 to 15:25 starts, 5 minutes each
MIN_SESSIONS = 20
MIN_BARS = 70        # a past day counts if it has at least this many of the 75 candles


def slot_of(hhmm):
    t = n.parse_hhmm(hhmm)
    mins = (t.hour * 60 + t.minute) - (9 * 60 + 15)
    if mins < 0 or mins % 5:
        raise SystemExit("timemachine.py: %s is not on the 5-minute grid from 9:15" % hhmm)
    return mins // 5


def slot_time(s):
    return (datetime.datetime(2000, 1, 1, 9, 15) + datetime.timedelta(minutes=5 * s)).strftime("%H:%M")


def full_sessions(bars, before):
    """Past days with at least MIN_BARS of the 75 candles (Yahoo's 60-day
    history often skips one or two). Each day is (date, slots, prev_close),
    slots being 75 entries: a candle, or None where Yahoo has a gap."""
    out = []
    prev_close = None
    for day, bs in n.sessions(bars):
        if day >= before:
            break
        slots = [None] * SLOTS
        for b in bs:
            m = b["t"].hour * 60 + b["t"].minute - (9 * 60 + 15)
            if m % 5 == 0 and 0 <= m // 5 < SLOTS:
                slots[m // 5] = b
        if sum(1 for x in slots if x) >= MIN_BARS and all(slots[:3]):
            out.append((day, slots, prev_close))
        prev_close = bs[-1]["c"]
    return out


def ratios(pool):
    """For each slot, a list of (o, h, l, c) ratios to the previous close."""
    by_slot = [[] for _ in range(SLOTS)]
    for day, slots, prev_close in pool:
        pc = prev_close
        for i, b in enumerate(slots):
            if b is None:
                continue
            if pc:
                by_slot[i].append((b["o"] / pc, b["h"] / pc, b["l"] / pc, b["c"] / pc))
            pc = b["c"]
    return by_slot


def walk(bars_iter, entry, stop, target):
    """Run candles forward. Returns ('stop'|'target'|'neither', last price)."""
    price = entry
    for o, h, l, c in bars_iter:
        if l <= stop:
            return "stop", stop
        if h >= target:
            return "target", target
        price = c
    return "neither", price


def replay(by_slot, start, end, entry, stop, target, rng, window):
    price = entry
    path = []
    for s in range(start, end):
        lo, hi = max(0, s - window), min(SLOTS - 1, s + window)
        cands = []
        while not cands:
            k = rng.randint(lo, hi)
            cands = by_slot[k]
        ro, rh, rl, rc = cands[rng.randrange(len(cands))]
        bar = (price * ro, price * rh, price * rl, price * rc)
        path.append(bar)
        price = bar[3]
    return walk(path, entry, stop, target)


def history(pool, plan, start, end, window_end):
    entry0, stop0, target0 = plan["entry"], plan["stop"], plan["target"]
    risk_pct = (entry0 - stop0) / entry0
    R = (target0 - entry0) / (entry0 - stop0)
    res = []
    for day, slots, prev_close in pool:
        if plan.get("setup") == "orb":
            o = n.opening_range(slots[:3])
            fire = None
            for i in range(3, window_end + 1):
                if slots[i] and slots[i]["c"] > o["high"]:
                    fire = i
                    break
            if fire is None or fire + 1 >= end:
                continue
            e = slots[fire]["c"]
            rule = plan.get("stop_rule", "")
            st = o["low"] if rule == "or-low" else o["mid"] if rule == "or-mid" else e * (1 - risk_pct)
            if st >= e:
                continue
            tg = e + R * (e - st)
            first = fire + 1
        else:
            before = [b for b in slots[:start] if b]
            if not before:
                continue
            e = before[-1]["c"]
            st, tg = e * (1 - risk_pct), e * (1 + R * risk_pct)
            first = start
        out, last = walk([(b["o"], b["h"], b["l"], b["c"]) for b in slots[first:end] if b], e, st, tg)
        r = R if out == "target" else -1.0 if out == "stop" else (last - e) / (e - st)
        res.append((str(day), out, round(r, 3)))
    return res


def verdict(tf, sf, R):
    hit = tf + sf
    if hit == 0:
        return "No replay reached the stop or the target before the end time."
    share = tf / hit * 100
    need = 100 / (1 + R)
    d = share - need
    if abs(d) < 5:
        word = "Close to a coin flip" if abs(R - 1) < 0.05 else "Close to break-even"
    elif abs(d) < 15:
        word = "Leans toward the target" if d > 0 else "Leans toward the stop"
    else:
        word = "Strongly toward the target" if d > 0 else "Strongly toward the stop"
    return "%s: of the replays that hit a side, the target came first %.1f%% of the time; a %.1fR target needs %.1f%% to break even." % (word, share, R, need)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--plan", default=None, help="plan file (default trader-data/plan.json)")
    ap.add_argument("--symbol")
    ap.add_argument("--entry", type=float)
    ap.add_argument("--stop", type=float)
    ap.add_argument("--target", type=float)
    ap.add_argument("--entry-time", help="HH:MM, the time the trade starts (on the 5-minute grid)")
    ap.add_argument("--setup", help="orb, or anything else for 'same time every day'")
    ap.add_argument("--stop-rule", help="or-low / or-mid for orb history")
    ap.add_argument("--day", help="the plan's day, YYYY-MM-DD (default: the latest session)")
    ap.add_argument("--until", help="end each replay at HH:MM (default the plan's flat-by, 15:20)")
    ap.add_argument("--replays", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=19)
    ap.add_argument("--window", type=int, default=2)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    plan = {}
    if not a.symbol:
        plan = n.read_json(a.plan or n.data_path("plan.json"))
        if not plan:
            sys.exit("timemachine.py: no trader-data/plan.json. Run /nse-plan with --write first, or pass --symbol --entry --stop --target --entry-time.")
    for k in ("symbol", "entry", "stop", "target", "setup", "day"):
        v = getattr(a, k)
        if v is not None:
            plan[k] = v
    if a.entry_time:
        plan["entry_time"] = a.entry_time
    if a.stop_rule:
        plan["stop_rule"] = a.stop_rule
    for k in ("symbol", "entry", "stop", "target"):
        if plan.get(k) in (None, ""):
            sys.exit("timemachine.py: the plan has no %s" % k)
    if not plan.get("entry_time"):
        sys.exit("timemachine.py: the plan has no entry time. Pass --entry-time HH:MM (for example 10:15).")
    entry, stop, target = float(plan["entry"]), float(plan["stop"]), float(plan["target"])
    if stop >= entry or target <= entry:
        sys.exit("timemachine.py: the plan needs stop < entry < target (buy first, sell later).")
    R = (target - entry) / (entry - stop)
    until = a.until or plan.get("flat_by") or "15:20"
    start, end = slot_of(plan["entry_time"]), slot_of(until)
    if end <= start:
        sys.exit("timemachine.py: the end time %s is not after the entry time %s" % (until, plan["entry_time"]))

    try:
        bars, meta = n.chart(plan["symbol"], rng="60d", interval="5m")
    except n.DataError as e:
        sys.exit("timemachine.py: %s" % e)
    day = datetime.date.fromisoformat(plan["day"]) if plan.get("day") else n.sessions(bars)[-1][0]
    pool = full_sessions(bars, day)
    sym = n.plain(meta["symbol"])
    if len(pool) < MIN_SESSIONS:
        print("Time Machine: %s has only %d full past session(s) before %s. It needs at least %d for fair odds." % (sym, len(pool), day, MIN_SESSIONS))
        print("A stock that just listed has no history to replay. Practise the method on an older stock (for example RELIANCE or TITAN),")
        print("and come back to this one after a month of trading.")
        sys.exit(2)

    by_slot = ratios(pool)
    rng = random.Random(a.seed)
    counts = {"target": 0, "stop": 0, "neither": 0}
    rs_, closes = [], []
    green = 0
    for _ in range(a.replays):
        out, last = replay(by_slot, start, end, entry, stop, target, rng, a.window)
        counts[out] += 1
        r = R if out == "target" else -1.0 if out == "stop" else (last - entry) / (entry - stop)
        rs_.append(r)
        if out == "neither":
            closes.append(last)
        if out == "target" or (out == "neither" and last > entry):
            green += 1
    N = a.replays
    tf, sf, nf = (counts[k] / N * 100 for k in ("target", "stop", "neither"))
    avg_r = statistics.mean(rs_)

    wend = min(slot_of(n.config()["entry_window"][1]), end - 1)
    hist = history(pool, plan, start, end, wend)
    hc = {"target": 0, "stop": 0, "neither": 0}
    for _, out, _ in hist:
        hc[out] += 1
    h_avg = statistics.mean([r for _, _, r in hist]) if hist else None
    v = verdict(counts["target"], counts["stop"], R)

    print("TIME MACHINE  %s  entry %s at %s, stop %s, target %s (%.2fR)" % (sym, n.rs(entry), plan["entry_time"], n.rs(stop), n.rs(target), R))
    print("Pool: %d full sessions before %s (%s to %s). Seed %d." % (len(pool), day, pool[0][0], pool[-1][0], a.seed))
    print()
    print("%s replays of the rest of the day, %s to %s (%d five-minute candles):" % (format(N, ","), plan["entry_time"], until, end - start))
    print("  target first   %5.1f %%" % tf)
    print("  stop first     %5.1f %%" % sf)
    print("  neither        %5.1f %%   still open at %s" % (nf, until))
    print("  green          %5.1f %%   target first, or above the entry at %s" % (green / N * 100, until))
    if closes:
        closes.sort()
        q = lambda p: closes[min(len(closes) - 1, int(p * len(closes)))]  # noqa: E731
        print("  Price at %s for the 'neither' replays: median %s, 90%% between %s and %s." % (until, n.rs(q(0.5)), n.rs(q(0.05)), n.rs(q(0.95))))
    print("  Average R: %+.3f" % avg_r)
    print()
    rule = "the opening-range breakout rule" if plan.get("setup") == "orb" else "buying at %s every day with the same stop and target distances" % plan["entry_time"]
    if hist:
        print("History: %s on each of those %d real days fired %d times: %d target, %d stop, %d neither. Average R %+.3f." % (
            rule, len(pool), len(hist), hc["target"], hc["stop"], hc["neither"], h_avg))
    else:
        print("History: %s never fired in those %d days." % (rule, len(pool)))
    print(v)
    if nf > 40:
        print("%.1f%% of the replays hit neither by %s; the price at %s decides those." % (nf, until, until))
    lean_target = v.startswith(("Leans toward the target", "Strongly toward the target"))
    lean_stop = v.startswith(("Leans toward the stop", "Strongly toward the stop"))
    if (lean_target and avg_r < 0) or (lean_stop and avg_r > 0):
        print("But the average R is %+.3f, the other way, because of the replays that hit neither." % avg_r)
    print()
    print("Built from %s's own last 60 days of 5-minute candles. A simulation, not a prediction: results, news and halts can do things those days never did." % sym)

    if a.write:
        n.write_json(n.data_path("timemachine.json"), {
            "plan": plan, "seed": a.seed, "replays": N, "until": until, "pool_sessions": len(pool),
            "mc": {"target_first": round(tf, 1), "stop_first": round(sf, 1), "neither": round(nf, 1),
                   "green": round(green / N * 100, 1), "avg_r": round(avg_r, 3)},
            "history": {"fired": len(hist), **hc, "avg_r": round(h_avg, 3) if h_avg is not None else None,
                        "days": hist},
            "verdict": v})
        print("Saved trader-data/timemachine.json")


if __name__ == "__main__":
    main()
