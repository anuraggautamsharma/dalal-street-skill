#!/usr/bin/env python3
"""Trade Planner: entry, stop-loss, target, size, charges and a PASS/BLOCK check.

  plan.py JPL --entry 1425 --stop 1410 --target 1455
  plan.py JPL --entry last --stop or-low --target 2R
  plan.py TITAN --entry 4390 --stop or-mid --target 2R --setup orb --write
  plan.py JPL --entry 1425 --stop 1410 --target 1455 --kind delivery

--entry   a price, or "last" (the latest price)
--stop    a price, or or-low / or-mid (the opening-range box) / vwap
--target  a price, or a multiple of the risk like 2R
Size comes from your rules in trader-data/config.json (default: Rs 1,00,000
paper account, risk 1% a trade): shares = max loss / (entry - stop), never
more than the account can pay for. Charges are Groww's, estimated.

Checks, each PASS, WARN or BLOCK:
  long only, stop below entry, target above; at least 1 share; the loss at
  the stop within the risk %; reward:risk at least the minimum; inside the
  entry window; trades today and the day's loss under the limits (from the
  paper log); and warnings for tight stops, charges eating the target, and
  stocks with very little history.
Any BLOCK means: do not take this trade. --write saves trader-data/plan.json.
"""
import argparse
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse-lib"))
import nselib as n  # noqa: E402


def resolve(sym, entry, stop, target, now, exchange):
    need = any(isinstance(x, str) and not _num(x) for x in (entry, stop))
    info = {}
    bars = meta = None
    try:
        bars, meta = n.chart(sym, rng="5d", interval="5m", exchange=exchange)
    except n.DataError as e:
        if need:
            raise
        info["data_error"] = str(e)
    if bars:
        if now:
            bars = n.upto(bars, now) or bars
        sess = n.sessions(bars)
        info["sessions_seen"] = len(sess)
        info["first_trade"] = meta.get("firstTradeDate")
        info["name"] = meta.get("longName") or meta.get("shortName")
        today = sess[-1][1]
        info["day"] = str(sess[-1][0])
        info["last"] = today[-1]["c"]
        orr = n.opening_range(today)
        info["or"] = orr
        info["vwap"] = n.vwap(today)
    if entry == "last":
        entry = info["last"]
    entry = float(entry)
    if isinstance(stop, str) and not _num(stop):
        key = {"or-low": ("or", "low"), "or-mid": ("or", "mid"), "vwap": ("vwap", None)}.get(stop)
        if not key:
            raise SystemExit("plan.py: --stop must be a price, or-low, or-mid or vwap")
        stop = info[key[0]][key[1]] if key[1] else info[key[0]]
    stop = float(stop)
    if isinstance(target, str) and target.upper().endswith("R"):
        mult = float(target[:-1])
        target = round(entry + mult * (entry - stop), 2)
    target = float(target)
    return entry, stop, target, info


def _num(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def today_stats(day):
    st = n.read_json(n.data_path("paper.json"), {}) or {}
    closed = [t for t in st.get("closed", []) if str(t.get("exit_time", ""))[:10] == day]
    opened = [t for t in st.get("closed", []) + st.get("open", []) if str(t.get("entry_time", ""))[:10] == day]
    return len(opened), round(sum(t.get("net", 0) for t in closed), 2), st.get("cash")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbol")
    ap.add_argument("--entry", required=True)
    ap.add_argument("--stop", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--qty", type=int, help="force a share count instead of sizing by risk")
    ap.add_argument("--account", type=float, help="money in the account (default: paper cash, else config)")
    ap.add_argument("--risk-pct", type=float)
    ap.add_argument("--kind", choices=["intraday", "delivery"])
    ap.add_argument("--exchange", choices=["NSE", "BSE"])
    ap.add_argument("--setup", default="manual", help="a name for the setup, e.g. orb, bounce, breakout")
    ap.add_argument("--why", default="", help="one line: why this trade")
    ap.add_argument("--wrong-if", default="", help="one line: what would prove the idea wrong")
    ap.add_argument("--entry-time", help="HH:MM the trade starts, on the 5-minute grid (default: now, rounded down)")
    ap.add_argument("--now", help='pin the clock, "YYYY-MM-DD HH:MM"')
    ap.add_argument("--write", action="store_true", help="save to trader-data/plan.json")
    a = ap.parse_args()

    cfg = n.config()
    kind = a.kind or cfg["kind"]
    exchange = a.exchange or cfg["exchange"]
    now = n.now_ist(a.now)
    try:
        entry, stop, target, info = resolve(a.symbol, a.entry, a.stop, a.target, now if a.now else None, exchange)
    except n.DataError as e:
        sys.exit("plan.py: %s" % e)

    trades_today, pnl_today, paper_cash = today_stats(str(now.date()))
    account = a.account or paper_cash or cfg["account"]
    risk_pct = a.risk_pct if a.risk_pct is not None else cfg["risk_pct"]
    max_loss = account * risk_pct / 100
    per_share = entry - stop
    afford = math.floor(account * cfg["max_position_pct"] / 100 / entry)
    capped = False
    if a.qty:
        qty = a.qty
    elif per_share > 0:
        qty = math.floor(max_loss / per_share)
        if qty > afford:
            qty, capped = afford, True
    else:
        qty = 0
    buy = qty * entry
    ch_stop = n.charges(buy, qty * stop, kind, exchange, cfg["charges"])
    ch_tgt = n.charges(buy, qty * target, kind, exchange, cfg["charges"])
    loss = qty * (stop - entry) - ch_stop["total"]
    gain = qty * (target - entry) - ch_tgt["total"]
    rr = (target - entry) / per_share if per_share > 0 else 0
    rr_net = gain / -loss if loss < 0 else 0

    checks = []

    def check(state, text):
        checks.append((state, text))

    if per_share <= 0:
        check("BLOCK", "The stop-loss must be BELOW the entry (this pack only buys first, sells later).")
    if target <= entry:
        check("BLOCK", "The target must be ABOVE the entry.")
    if qty < 1:
        check("BLOCK", "Not even 1 share fits your risk limit. Pick a closer stop or a cheaper stock.")
    if per_share > 0 and qty >= 1:
        if qty * per_share > max_loss * 1.001:
            check("BLOCK", "Loss at the stop %s is more than your %.1f%% limit %s." % (n.rs(qty * per_share), risk_pct, n.rs(max_loss)))
        else:
            check("PASS", "Loss at the stop %s (plus charges) is within your %.1f%% limit %s." % (n.rs(qty * per_share), risk_pct, n.rs(max_loss)))
    if per_share > 0 and target > entry:
        if rr + 1e-9 < cfg["min_reward_risk"]:
            check("BLOCK", "Reward:risk is %.2f:1, under your minimum %.1f:1." % (rr, cfg["min_reward_risk"]))
        else:
            check("PASS", "Reward:risk is %.2f:1 (minimum %.1f:1)." % (rr, cfg["min_reward_risk"]))
    status = n.market_status(now)
    w0, w1 = (n.parse_hhmm(x) for x in cfg["entry_window"])
    if status != "open":
        check("WARN", "The market is %s right now, so this is a practice plan for later." % status.replace("-", " "))
    elif not (w0 <= now.time() <= w1):
        check("BLOCK" if kind == "intraday" else "WARN", "It is %s. Your entry window is %s to %s (the first 15 minutes are wild; late entries have no time to work)." % (n.hhmm(now), cfg["entry_window"][0], cfg["entry_window"][1]))
    else:
        check("PASS", "Inside your entry window %s to %s." % tuple(cfg["entry_window"]))
    if trades_today >= cfg["max_trades_per_day"]:
        check("BLOCK", "You already took %d trade(s) today; your limit is %d." % (trades_today, cfg["max_trades_per_day"]))
    limit = account * cfg["daily_loss_limit_pct"] / 100
    if pnl_today <= -limit:
        check("BLOCK", "Today's paper loss %s hit your daily limit %s. Done for today." % (n.rs(pnl_today), n.rs(-limit)))
    elif pnl_today < 0 and pnl_today + loss < -limit:
        check("WARN", "If this stop hits too, today's loss (%s) would pass your daily limit %s." % (n.rs(pnl_today + loss), n.rs(-limit)))
    if per_share > 0 and per_share / entry < 0.002:
        check("WARN", "The stop is only %.2f%% away. Normal wiggles may hit it." % (per_share / entry * 100))
    if gain > 0 and ch_tgt["total"] > 0.25 * qty * (target - entry):
        check("WARN", "Charges %s eat over a quarter of the target profit." % n.rs(ch_tgt["total"]))
    if capped:
        check("WARN", "Size was cut to %d shares because the account cannot pay for more." % qty)
    seen = info.get("sessions_seen")
    if seen is not None and seen < 5:
        check("WARN", "This stock has only %d trading day(s) of history: floors and ceilings are guesses." % seen)
    verdict = "BLOCK" if any(s == "BLOCK" for s, _ in checks) else "PASS"

    sym = n.to_yahoo(a.symbol, exchange)
    print("TRADE PLAN  %s %s  (%s, paper, %s)" % (n.plain(sym), "(" + info["name"] + ")" if info.get("name") else "", kind, exchange))
    print()
    print("  Buy        %d shares at %s   = %s" % (qty, n.rs(entry), n.rs(buy)))
    print("  Stop-loss  %s   (%s a share below)" % (n.rs(stop), n.rs(per_share)))
    print("  Target     %s   (%s a share above)" % (n.rs(target), n.rs(target - entry)))
    print("  Reward:risk %.2f : 1   (after charges %.2f : 1)" % (rr, rr_net))
    print()
    print("  If the stop hits:   %s   (%s price + %s charges)" % (n.rs(loss, True), n.rs(qty * (stop - entry)), n.rs(ch_stop["total"])))
    print("  If the target hits: %s   (%s price - %s charges)" % (n.rs(gain, True), n.rs(qty * (target - entry), True), n.rs(ch_tgt["total"])))
    print("  Account %s, risk %.1f%% = %s max loss" % (n.rs(account), risk_pct, n.rs(max_loss)))
    if kind == "intraday":
        print("  Close by %s if neither the stop nor the target hits." % cfg["flat_by"])
    print()
    for s, t in checks:
        print("  %-5s %s" % (s, t))
    print()
    print("VERDICT: %s" % ("PASS. The plan follows your rules." if verdict == "PASS" else "BLOCK. Do not take this trade as planned."))
    print("Charges are estimates (default: Groww's published rates; set yours in trader-data/config.json). Not advice: this is arithmetic on your plan.")

    entry_time = a.entry_time
    if not entry_time and n.market_status(now) == "open":
        entry_time = "%02d:%02d" % (now.hour, now.minute - now.minute % 5)
    plan = {"symbol": sym, "name": info.get("name"), "kind": kind, "exchange": exchange, "setup": a.setup,
            "made_at": str(now), "day": info.get("day"), "entry_time": entry_time, "entry": entry, "stop": stop, "stop_rule": a.stop if not _num(a.stop) else "price",
            "target": target, "target_r": round(rr, 2), "qty": qty,
            "money": round(buy, 2), "reward_risk": round(rr, 2), "loss_at_stop": round(loss, 2),
            "gain_at_target": round(gain, 2), "charges_at_stop": ch_stop, "charges_at_target": ch_tgt,
            "flat_by": cfg["flat_by"], "account": account, "risk_pct": risk_pct, "why": a.why,
            "wrong_if": a.wrong_if, "opening_range": info.get("or"), "verdict": verdict,
            "checks": [{"state": s, "text": t} for s, t in checks]}
    if a.write:
        n.write_json(n.data_path("plan.json"), plan)
        print("Saved trader-data/plan.json%s" % ("" if entry_time else " (no entry time: pass --entry-time HH:MM for the Time Machine)"))


if __name__ == "__main__":
    main()
