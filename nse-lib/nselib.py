"""Shared helpers for the India Trader skills.

NSE/BSE prices from Yahoo Finance's free chart endpoint, India time, NSE
stock lists, the Groww charge sheet, and the trader-data folder where every
skill reads and writes. Standard library only (Python 3.9+).
"""
import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 30)
PRE_OPEN = datetime.time(9, 0)
UA = "Mozilla/5.0"
CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/%s?%s"
LISTS = {
    "nifty50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "nifty100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "nifty500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
}
# Common names people type, mapped to the NSE symbol.
ALIASES = {"JIO": "JPL", "JIOPLATFORMS": "JPL", "JIO-PLATFORMS": "JPL", "NIFTY": "^NSEI",
           "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}

# Groww equity charges. These are estimates: rates change, so check
# groww.in/pricing and override any of them in trader-data/config.json "charges".
CHARGES = {
    "brokerage_pct": 0.001,        # 0.1% of the order value...
    "brokerage_max": 20.0,         # ...capped at Rs 20 per executed order
    "brokerage_min": 5.0,          # and at least Rs 5
    "stt_intraday_sell": 0.00025,  # 0.025% on the sell side, intraday
    "stt_delivery": 0.001,         # 0.1% on buy and sell, delivery
    "exchange_NSE": 0.0000297,     # NSE transaction charge
    "exchange_BSE": 0.0000375,     # BSE transaction charge
    "sebi": 0.000001,              # Rs 10 per crore
    "stamp_intraday_buy": 0.00003,
    "stamp_delivery_buy": 0.00015,
    "gst": 0.18,                   # on brokerage + exchange + SEBI fee
    "dp_per_sell": 13.5,           # delivery sell, per stock per day, before GST
}

DEFAULT_CONFIG = {
    "account": 100000,             # paper money, in rupees
    "risk_pct": 1.0,               # max loss per trade, % of account
    "min_reward_risk": 2.0,        # target must be at least 2x the risk
    "max_trades_per_day": 3,
    "daily_loss_limit_pct": 2.0,   # stop trading for the day after losing this much
    "entry_window": ["09:30", "14:30"],
    "flat_by": "15:20",            # intraday trades are closed by this time
    "max_position_pct": 100,       # most of the account one trade may use
    "kind": "intraday",            # intraday or delivery
    "exchange": "NSE",
    "paper": True,
    "language": "auto",            # auto (match the user), hi, hinglish or en
}


class DataError(Exception):
    pass


# ---------------------------------------------------------------- files

def data_dir():
    d = os.environ.get("TRADER_DATA") or os.path.join(os.getcwd(), "trader-data")
    os.makedirs(d, exist_ok=True)
    return d


def data_path(*parts):
    p = os.path.join(data_dir(), *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, default=str)
        f.write("\n")
    os.replace(tmp, path)


def config():
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(read_json(data_path("config.json"), {}) or {})
    ch = dict(CHARGES)
    ch.update(cfg.get("charges") or {})
    cfg["charges"] = ch
    return cfg


# ---------------------------------------------------------------- time

def now_ist(override=None):
    """The current India time, or a pinned one ("2026-10-29 12:10")."""
    if override:
        return datetime.datetime.strptime(override, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return datetime.datetime.now(IST).replace(microsecond=0)


def parse_hhmm(s):
    h, m = s.split(":")
    return datetime.time(int(h), int(m))


def market_status(now):
    """closed-weekend / before-open / pre-open / open / closed. Exchange
    holidays are not known offline: a weekday with no candles is one."""
    if now.weekday() >= 5:
        return "closed-weekend"
    t = now.time()
    if t < PRE_OPEN:
        return "before-open"
    if t < MARKET_OPEN:
        return "pre-open"
    if t < MARKET_CLOSE:
        return "open"
    return "closed"


def hhmm(dt):
    return dt.strftime("%H:%M")


# ---------------------------------------------------------------- symbols

def to_yahoo(sym, exchange="NSE"):
    s = sym.strip().upper().replace(" ", "")
    s = ALIASES.get(s, s)
    if s.startswith("^") or s.endswith(".NS") or s.endswith(".BO"):
        return s
    return s + (".BO" if exchange.upper() == "BSE" else ".NS")


def plain(sym):
    s = sym.upper()
    for suf in (".NS", ".BO"):
        if s.endswith(suf):
            return s[: -len(suf)]
    return s


def fetch(url, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                break
            time.sleep(1.5 * (i + 1))
        except (urllib.error.URLError, OSError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise DataError("could not fetch %s (%s)" % (url.split("?")[0], last))


def universe(name):
    """Symbols for nifty50 / nifty100 / nifty500, a comma list, or a file
    with one symbol per line. NSE lists are cached for a day."""
    if name in LISTS:
        cache = data_path("cache", name + ".csv")
        fresh = os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 86400
        if not fresh:
            body = fetch(LISTS[name]).decode("utf-8", "replace")
            with open(cache, "w") as f:
                f.write(body)
        with open(cache) as f:
            rows = f.read().splitlines()
        head = [h.strip() for h in rows[0].split(",")]
        i = head.index("Symbol")
        return [r.split(",")[i].strip() for r in rows[1:] if r.strip()]
    if os.path.exists(name):
        with open(name) as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    return [s.strip() for s in name.split(",") if s.strip()]


# ---------------------------------------------------------------- candles

def chart(sym, rng="1d", interval="5m", exchange="NSE"):
    """Candles as dicts {t (IST datetime), o, h, l, c, v} plus Yahoo's meta.
    Intraday candles keep only 9:15 to 15:25 starts; the zero-volume 15:30
    closing tick Yahoo appends is dropped."""
    ysym = to_yahoo(sym, exchange)
    q = urllib.parse.urlencode({"range": rng, "interval": interval})
    try:
        raw = json.loads(fetch(CHART_URL % (urllib.parse.quote(ysym), q)))
    except ValueError:
        raise DataError("Yahoo sent something that is not JSON for %s" % ysym)
    res = (raw.get("chart") or {}).get("result")
    if not res:
        err = ((raw.get("chart") or {}).get("error") or {}).get("description", "no data")
        raise DataError("Yahoo has no data for %s: %s" % (ysym, err))
    r = res[0]
    meta = r.get("meta", {})
    ts = r.get("timestamp") or []
    quote = (r.get("indicators", {}).get("quote") or [{}])[0]
    intraday = interval.endswith("m") or interval.endswith("h")
    out = []
    closes = {}
    for i, t in enumerate(ts):
        o, h, l, c, v = (quote.get(k, [None] * len(ts))[i] for k in ("open", "high", "low", "close", "volume"))
        if None in (o, h, l, c):
            continue
        dt = datetime.datetime.fromtimestamp(t, IST)
        if intraday and dt.time() >= MARKET_CLOSE:
            closes[dt.date()] = round(c, 2)  # the official closing price tick
            continue
        if intraday and dt.time() < MARKET_OPEN and not ysym.startswith("^"):
            continue
        out.append({"t": dt, "o": round(o, 2), "h": round(h, 2), "l": round(l, 2), "c": round(c, 2), "v": int(v or 0)})
    if not out:
        raise DataError("no candles for %s in range %s" % (ysym, rng))
    meta["symbol"] = ysym
    meta["closes"] = closes
    return out, meta


def sessions(bars):
    """Group intraday candles by trading day: [(date, [bars])], oldest first."""
    days = {}
    for b in bars:
        days.setdefault(b["t"].date(), []).append(b)
    return sorted(days.items())


def daily_closes(sym, exchange="NSE"):
    """Official closing prices by date, from daily candles. NSE's close is the
    volume-weighted average of the last 30 minutes, not the last trade."""
    try:
        days, _ = chart(sym, rng="1mo", interval="1d", exchange=exchange)
    except DataError:
        return {}
    return {b["t"].date(): b["c"] for b in days}


def day_close(meta, day, day_bars, official=None):
    """The official close for a day when known, else Yahoo's 15:30 tick, else the last candle."""
    if official and day in official:
        return official[day]
    return meta.get("closes", {}).get(day, day_bars[-1]["c"])


def upto(bars, when):
    """Candles that had finished by `when` (a 5-minute bar starting 12:10 is done at 12:15)."""
    return [b for b in bars if b["t"] + datetime.timedelta(minutes=5) <= when]


def vwap(bars):
    pv = sum((b["h"] + b["l"] + b["c"]) / 3 * b["v"] for b in bars)
    vol = sum(b["v"] for b in bars)
    return round(pv / vol, 2) if vol else None


def opening_range(day_bars, minutes=15):
    n = max(1, minutes // 5)
    rng = day_bars[:n]
    if len(rng) < n:
        return None
    hi = max(b["h"] for b in rng)
    lo = min(b["l"] for b in rng)
    return {"high": hi, "low": lo, "mid": round((hi + lo) / 2, 2), "end": hhmm(rng[-1]["t"] + datetime.timedelta(minutes=5))}


def levels(bars, price, width_pct=0.25, wing=2):
    """Floors and ceilings: swing lows and highs (a candle lower or higher
    than the `wing` candles on each side), grouped when within width_pct %.
    Returns (floors below price, ceilings above price), nearest first,
    each {price, touches}."""
    pts = []
    for i in range(wing, len(bars) - wing):
        lows = [bars[j]["l"] for j in range(i - wing, i + wing + 1)]
        highs = [bars[j]["h"] for j in range(i - wing, i + wing + 1)]
        if bars[i]["l"] == min(lows):
            pts.append(bars[i]["l"])
        if bars[i]["h"] == max(highs):
            pts.append(bars[i]["h"])
    pts.sort()
    groups = []
    for p in pts:
        if groups and (p - groups[-1][0]) / groups[-1][0] * 100 <= width_pct:
            groups[-1].append(p)
        else:
            groups.append([p])
    lv = [{"price": round(sum(g) / len(g), 2), "touches": len(g)} for g in groups]
    floors = sorted([x for x in lv if x["price"] < price], key=lambda x: -x["price"])
    ceilings = sorted([x for x in lv if x["price"] > price], key=lambda x: x["price"])
    return floors, ceilings


def rsi(closes, n=14):
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 1)


# ---------------------------------------------------------------- charges

def charges(buy_value, sell_value, kind="intraday", exchange="NSE", rates=None):
    """Estimated Groww charges for one round trip (one buy order, one sell order)."""
    r = rates or CHARGES

    def brokerage(v):
        if v <= 0:
            return 0.0
        return min(r["brokerage_max"], max(r["brokerage_min"], v * r["brokerage_pct"]))

    brk = brokerage(buy_value) + brokerage(sell_value)
    if kind == "delivery":
        stt = (buy_value + sell_value) * r["stt_delivery"]
        stamp = buy_value * r["stamp_delivery_buy"]
        dp = r["dp_per_sell"] * (1 + r["gst"]) if sell_value > 0 else 0.0
    else:
        stt = sell_value * r["stt_intraday_sell"]
        stamp = buy_value * r["stamp_intraday_buy"]
        dp = 0.0
    exch = (buy_value + sell_value) * r["exchange_" + exchange.upper()]
    sebi = (buy_value + sell_value) * r["sebi"]
    gst = (brk + exch + sebi) * r["gst"]
    parts = {"brokerage": brk, "stt": stt, "exchange": exch, "sebi": sebi, "stamp": stamp, "gst": gst, "dp": dp}
    parts = {k: round(v, 2) for k, v in parts.items()}
    parts["total"] = round(sum(parts.values()), 2)
    return parts


# ---------------------------------------------------------------- printing

def rs(x, sign=False):
    """Indian-style rupees: 94050 -> ₹94,050; 1425.5 -> ₹1,425.50; 1234567 -> ₹12,34,567."""
    neg = x < 0
    x = abs(x)
    whole = int(round(x * 100)) // 100
    paise = int(round(x * 100)) % 100
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    out = "₹" + s + (".%02d" % paise if paise else "")
    if neg:
        return "-" + out
    return ("+" + out) if sign else out


def pct(a, b):
    return round((a - b) / b * 100, 2) if b else 0.0
