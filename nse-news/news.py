#!/usr/bin/env python3
"""News Check: recent headlines for NSE/BSE stocks, in India time, tagged.

  news.py JPL                     last 48 hours
  news.py JPL,RELIANCE --hours 12
  news.py --from-plan             the stock in trader-data/plan.json

Headlines come from Yahoo Finance's free RSS feed (it can be thin for some
Indian stocks). Tags flag the kinds of news that move prices: results,
dividends, big orders, deals, SEBI, ratings and targets, block deals,
management changes. Also prints today's move so you can see the reaction.
Official company filings live on nseindia.com (Corporate Announcements):
check there for anything that matters.
"""
import argparse
import datetime
import email.utils
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse-lib"))
import nselib as n  # noqa: E402

RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?%s"
TAGS = [
    ("results", ("result", "earnings", "profit", "quarter", "q1", "q2", "q3", "q4", "revenue", "ebitda")),
    ("dividend/bonus/split", ("dividend", "bonus", "split", "buyback")),
    ("order/contract", ("order", "contract", "wins", "bags")),
    ("deal", ("acquire", "acquisition", "merger", "stake", "deal", "invest")),
    ("regulator", ("sebi", "rbi", "penalty", "probe", "ban", "trai", "government")),
    ("rating/target", ("target", "rating", "upgrade", "downgrade", "buy call", "sell call", "brokerage")),
    ("block deal", ("block deal", "bulk deal", "offload", "sells shares")),
    ("listing/IPO", ("ipo", "listing", "debut", "lists")),
    ("management", ("ceo", "cfo", "resigns", "appoint", "chairman")),
]


def tags_for(text):
    t = text.lower()
    return [name for name, words in TAGS if any(w in t for w in words)]


def headlines(sym, hours, now):
    q = urllib.parse.urlencode({"s": n.to_yahoo(sym), "region": "IN", "lang": "en-IN"})
    try:
        root = ET.fromstring(n.fetch(RSS % q))
    except ET.ParseError:
        raise n.DataError("the news feed for %s was not readable" % sym)
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        when = it.findtext("pubDate")
        try:
            dt = email.utils.parsedate_to_datetime(when).astimezone(n.IST)
        except (TypeError, ValueError):
            continue
        if now - dt > datetime.timedelta(hours=hours):
            continue
        desc = (it.findtext("description") or "").strip()
        out.append({"time": dt, "title": title, "link": it.findtext("link"), "tags": tags_for(title + " " + desc)})
    return sorted(out, key=lambda x: x["time"], reverse=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="?")
    ap.add_argument("--hours", type=float, default=48)
    ap.add_argument("--from-plan", action="store_true")
    ap.add_argument("--now")
    a = ap.parse_args()
    if a.from_plan:
        plan = n.read_json(n.data_path("plan.json")) or {}
        syms = [plan.get("symbol")] if plan.get("symbol") else []
    else:
        syms = n.universe(a.symbols) if a.symbols else []
    if not syms:
        sys.exit("news.py: name a stock, e.g. news.py JPL")
    now = n.now_ist(a.now)
    saved = {}
    for s in syms:
        print("== %s ==" % n.plain(n.to_yahoo(s)))
        try:
            bars, meta = n.chart(s, rng="1d", interval="5m")
            prev = meta.get("chartPreviousClose")
            last = n.day_close(meta, bars[-1]["t"].date(), bars, n.daily_closes(s))
            if prev:
                print("Move: %s, %+.2f%% vs the previous close %s (%s)." % (n.rs(last), n.pct(last, prev), n.rs(prev), bars[-1]["t"].date()))
        except n.DataError as e:
            print("Move: %s" % e)
        try:
            hl = headlines(s, a.hours, now)
        except n.DataError as e:
            print("News: %s" % e)
            continue
        if not hl:
            print("No headlines in the last %g hours on Yahoo. Check nseindia.com > Corporate Announcements too." % a.hours)
        for h in hl[:12]:
            age = now - h["time"]
            ago = "%dh ago" % (age.total_seconds() // 3600) if age.total_seconds() >= 3600 else "%dm ago" % (age.total_seconds() // 60)
            print("  %s (%s)  %s%s" % (h["time"].strftime("%d %b %H:%M"), ago, h["title"], "  [" + ", ".join(h["tags"]) + "]" if h["tags"] else ""))
        saved[s] = [dict(h, time=str(h["time"])) for h in hl]
        print()
    print("Headlines are not facts about the future. Big news days are wild: many traders simply stay out.")
    n.write_json(n.data_path("news.json"), saved)


if __name__ == "__main__":
    main()
