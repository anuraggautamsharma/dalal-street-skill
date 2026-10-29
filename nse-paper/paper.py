#!/usr/bin/env python3
"""Paper Trader: fake-money trades, checked against real NSE candles.

  paper.py init --cash 100000          start (or restart) the paper account
  paper.py open                        open the trade in trader-data/plan.json (needs a PASS)
  paper.py open --price 1425.20        ...at the price you would really have paid
  paper.py check                       walk the candles since entry: stop? target? 15:20?
  paper.py close --id 2 --price 1440   close by hand
  paper.py status                      cash, open trades, live P&L
  paper.py log                         every closed trade, wins, losses, total

How `check` decides, candle by candle after the entry (5-minute candles):
  - the low reaches the stop  -> out at the stop, or at the candle's open if
    it opened below the stop already (a gap: real stops slip like this)
  - the high reaches the target -> out at the target (or the open, if above)
  - a candle that touches both counts as the stop (the careful assumption)
  - intraday and still open at the flat-by time (15:20) -> out at that price
Charges are Groww's, estimated. Nothing here touches a real broker.
State lives in trader-data/paper.json.
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse-lib"))
import nselib as n  # noqa: E402

STATE = None


def load():
    st = n.read_json(n.data_path("paper.json"))
    if not st:
        sys.exit("paper.py: no paper account yet. Run: paper.py init --cash 100000")
    return st


def save(st):
    n.write_json(n.data_path("paper.json"), st)


def close_trade(st, t, price, when, reason):
    cfg = n.config()
    ch = n.charges(t["qty"] * t["entry"], t["qty"] * price, t["kind"], t["exchange"], cfg["charges"])
    gross = round(t["qty"] * (price - t["entry"]), 2)
    t.update(exit=round(price, 2), exit_time=str(when), reason=reason, gross=gross, charges=ch["total"],
             net=round(gross - ch["total"], 2))
    risk = t["qty"] * (t["entry"] - t["stop"])
    t["r"] = round(gross / risk, 2) if risk > 0 else None
    st["cash"] = round(st["cash"] + t["qty"] * price - ch["total"], 2)
    st["open"].remove(t)
    st["closed"].append(t)
    print("CLOSED #%d %s: %s %d at %s (%s). Gross %s, charges %s, net %s (%+.2fR)." % (
        t["id"], t["symbol"], reason, t["qty"], n.rs(price), str(when)[11:16], n.rs(gross, True), n.rs(ch["total"]),
        n.rs(t["net"], True), t["r"] or 0))
    print("Diary line: | #%d | %s | %s | %s → %s | %d | %s | %s |" % (
        t["id"], t["entry_time"][:10], n.plain(t["symbol"]), n.rs(t["entry"]), n.rs(price), t["qty"], reason, n.rs(t["net"], True)))


def cmd_init(a):
    st = {"start": a.start or a.cash, "cash": a.cash, "open": [], "closed": [], "next_id": a.next_id}
    save(st)
    print("Paper account ready: %s cash. Fake money only." % n.rs(a.cash))


def cmd_open(a):
    st = load()
    plan = n.read_json(n.data_path("plan.json"))
    if not plan:
        sys.exit("paper.py: no trader-data/plan.json. Make one with /nse-plan --write.")
    if plan.get("verdict") != "PASS":
        sys.exit("paper.py: the plan's verdict is %s. A BLOCKed plan is not traded, not even on paper." % plan.get("verdict"))
    now = n.now_ist(a.now)
    price = a.price or plan["entry"]
    need = plan["qty"] * price
    if need > st["cash"] + 0.01:
        sys.exit("paper.py: this needs %s but the paper account has %s." % (n.rs(need), n.rs(st["cash"])))
    t = {"id": st["next_id"], "symbol": plan["symbol"], "kind": plan["kind"], "exchange": plan["exchange"],
         "setup": plan.get("setup"), "qty": plan["qty"], "entry": round(price, 2), "stop": plan["stop"],
         "target": plan["target"], "flat_by": plan.get("flat_by", "15:20"),
         "entry_time": str(now) if not a.at else "%s %s:00+05:30" % (now.date(), a.at),
         "why": plan.get("why", ""), "wrong_if": plan.get("wrong_if", "")}
    st["next_id"] += 1
    st["cash"] = round(st["cash"] - need, 2)
    st["open"].append(t)
    save(st)
    print("OPENED #%d (paper): BUY %d %s at %s = %s. Stop %s, target %s%s." % (
        t["id"], t["qty"], n.plain(t["symbol"]), n.rs(price), n.rs(need), n.rs(t["stop"]), n.rs(t["target"]),
        ", out by " + t["flat_by"] if t["kind"] == "intraday" else ""))
    print("Paper cash left: %s" % n.rs(st["cash"]))


def cmd_check(a):
    st = load()
    if not st["open"]:
        print("No open paper trades.")
        return
    now = n.now_ist(a.now)
    for t in list(st["open"]):
        et = datetime.datetime.fromisoformat(t["entry_time"])
        try:
            bars, meta = n.chart(t["symbol"], rng="5d", interval="5m", exchange=t["exchange"])
        except n.DataError as e:
            print("#%d %s: %s" % (t["id"], t["symbol"], e))
            continue
        bars = [b for b in n.upto(bars, now) if b["t"] >= et]
        flat_by = n.parse_hhmm(t["flat_by"])
        done = False
        for b in bars:
            if t["kind"] == "intraday" and b["t"].time() >= flat_by:
                close_trade(st, t, b["o"], b["t"], "flat by %s" % t["flat_by"])
                done = True
                break
            end = b["t"] + datetime.timedelta(minutes=5)
            if b["l"] <= t["stop"]:
                close_trade(st, t, min(t["stop"], b["o"]), end, "stop-loss" + (" (gapped, slipped)" if b["o"] < t["stop"] else ""))
                done = True
                break
            if b["h"] >= t["target"]:
                close_trade(st, t, max(t["target"], b["o"]), end, "target")
                done = True
                break
        if done:
            continue
        if t["kind"] == "intraday" and now.time() >= flat_by and bars and bars[-1]["t"].date() == et.date():
            close_trade(st, t, bars[-1]["c"], now, "flat by %s" % t["flat_by"])
            continue
        last = bars[-1]["c"] if bars else t["entry"]
        live = t["qty"] * (last - t["entry"])
        print("#%d %s open: %d at %s, now %s (%s on paper). Stop %s is %.2f%% below, target %s is %.2f%% above." % (
            t["id"], n.plain(t["symbol"]), t["qty"], n.rs(t["entry"]), n.rs(last), n.rs(live, True),
            n.rs(t["stop"]), -n.pct(t["stop"], last), n.rs(t["target"]), n.pct(t["target"], last)))
    save(st)


def cmd_close(a):
    st = load()
    t = next((x for x in st["open"] if x["id"] == a.id), None)
    if not t:
        sys.exit("paper.py: no open trade #%d" % a.id)
    close_trade(st, t, a.price, n.now_ist(a.now), a.reason)
    save(st)


def cmd_status(a):
    st = load()
    closed = st["closed"]
    net = sum(t["net"] for t in closed)
    print("Paper account: started %s, cash %s, closed P&L %s over %d trade(s)." % (
        n.rs(st["start"]), n.rs(st["cash"]), n.rs(net, True), len(closed)))
    for t in st["open"]:
        print("  open #%d %s: %d at %s, stop %s, target %s (since %s)" % (
            t["id"], n.plain(t["symbol"]), t["qty"], n.rs(t["entry"]), n.rs(t["stop"]), n.rs(t["target"]), t["entry_time"][:16]))
    if st["open"]:
        print("Run paper.py check for live prices.")


def cmd_log(a):
    st = load()
    c = st["closed"]
    if not c:
        print("No closed paper trades yet.")
        return
    print("| # | date | stock | entry → exit | qty | how | net | R |")
    print("|---|---|---|---|---|---|---|---|")
    for t in c:
        print("| %d | %s | %s | %s → %s | %d | %s | %s | %s |" % (
            t["id"], t["entry_time"][:10], n.plain(t["symbol"]), n.rs(t["entry"]), n.rs(t["exit"]), t["qty"],
            t["reason"], n.rs(t["net"], True), "%+.2f" % t["r"] if t.get("r") is not None else "-"))
    wins = [t for t in c if t["net"] > 0]
    total = sum(t["net"] for t in c)
    rs_ = [t["r"] for t in c if t.get("r") is not None]
    print()
    print("%d trades: %d win(s), %d loss(es) (%.0f%% wins). Net %s. Average R %s." % (
        len(c), len(wins), len(c) - len(wins), len(wins) / len(c) * 100, n.rs(total, True),
        "%+.2f" % (sum(rs_) / len(rs_)) if rs_ else "-"))
    if len(c) < 20:
        print("Fewer than 20 trades: too few to judge a method yet. Keep logging.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--cash", type=float, required=True)
    p.add_argument("--start", type=float, help="the starting amount, if cash already moved")
    p.add_argument("--next-id", type=int, default=1, help="number of the next trade")
    p = sub.add_parser("open")
    p.add_argument("--price", type=float)
    p.add_argument("--at", help="HH:MM the trade was entered, if not now")
    p.add_argument("--now")
    p = sub.add_parser("check")
    p.add_argument("--now")
    p = sub.add_parser("close")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--reason", default="closed by hand")
    p.add_argument("--now")
    sub.add_parser("status")
    sub.add_parser("log")
    a = ap.parse_args()
    {"init": cmd_init, "open": cmd_open, "check": cmd_check, "close": cmd_close, "status": cmd_status, "log": cmd_log}[a.cmd](a)


if __name__ == "__main__":
    main()
