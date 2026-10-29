#!/usr/bin/env python3
"""Builds assets/demo.svg: a looping terminal demo for the README.

  python3 assets/make_demo.py

Four scenes, real output from the NSE session of 29 October 2026:
scan -> plan -> time machine -> a Hinglish chart explanation.
"""
import os
from xml.sax.saxutils import escape

W, H = 920, 560
SCENE = 6.0                     # seconds per scene
LINE_H = 24
X0, Y0 = 28, 96
C = {"text": "#E6EDF3", "dim": "#8B949E", "prompt": "#79C0FF", "green": "#3FB950", "red": "#F85149",
     "orange": "#FF9F45", "claude": "#D97757", "white": "#FFFFFF"}

# Each scene: (label, prompt, [(text, colour, bold) or ("bar", value_pct, colour)])
SCENES = [
    ("Scan", "Scan the Nifty 50 for opening-range breakouts", [
        ("⏺ nse-scanner · 50 stocks · box 9:15 to 9:30 · candles up to 10:15", "claude", False),
        ("  26 broke out UP · 11 broke DOWN · 13 still inside the box", "text", False),
        ("", "text", False),
        ("  stock        time    box top     close    vol   now", "dim", False),
        ("  TITAN        09:35   4381.10   4390.30   2.7x   holding 4401.50", "green", False),
        ("  ADANIENT     09:35   2505.20   2505.70   1.8x   holding 2544.00", "green", False),
        ("  EICHERMOT    09:55   7290.50   7294.00   1.5x   fell back 7262.50", "orange", False),
        ("", "text", False),
        ("  A scan finds candidates, not trades. Next: read the chart, then plan.", "dim", False),
    ]),
    ("Plan", "Plan TITAN: stop at the box middle, target 2R", [
        ("⏺ nse-plan · TITAN · intraday · paper · NSE", "claude", False),
        ("  Buy 22 shares at ₹4,390.30 = ₹96,586.60   (1% risk rule)", "text", False),
        ("  Stop-loss ₹4,361.85 · Target ₹4,447.20 · Reward:risk 2.00 : 1", "text", False),
        ("  If the stop hits:    -₹706.96   (incl. ₹81.06 STT, brokerage, GST...)", "red", False),
        ("  If the target hits:  +₹1,170.21 (incl. ₹81.59 charges)", "green", False),
        ("", "text", False),
        ("  PASS  Loss at the stop is within your 1% limit (₹1,000)", "green", False),
        ("  PASS  Reward:risk 2.00:1 · PASS  Inside the entry window 09:30-14:30", "green", False),
        ("  VERDICT: PASS. The plan follows your rules.", "white", True),
    ]),
    ("Odds", "Run the time machine", [
        ("⏺ nse-timemachine · 10,000 replays · 59 past sessions · seed 19", "claude", False),
        ("  target first   11.5 %", "green", False),
        ("  stop first     50.0 %", "red", False),
        ("  neither        38.6 %", "dim", False),
        ("  History: the rule fired 35 times: 9 target, 18 stop, 8 neither", "text", False),
        ("", "text", False),
        ("  Leans toward the stop: the target came first 18.7% of the time;", "orange", True),
        ("  a 2R target needs 33.3% to break even.", "orange", True),
        ("  A simulation from 60 days of candles, not a prediction.", "dim", False),
    ]),
    ("Hindi", "Jio ka chart samjhao", [
        ("⏺ nse-chart · JPL (Jio Platforms) · 29 Oct 2026", "claude", False),
        ("  Jio ₹1,421.60 par band hua, kal ke close ₹1,417.50 se +0.29%.", "text", False),
        ("  Subah gap-up khula (₹1,444), phir opening box ke neeche aa gaya.", "text", False),
        ("  Price VWAP (₹1,436.65) ke neeche hai, yaani aaj sellers control mein the.", "text", False),
        ("", "text", False),
        ("  Sabse paas ka floor  ₹1,418.97  (4 baar touch)", "green", False),
        ("  Sabse paas ki ceiling ₹1,424.42 (6 baar touch)", "red", False),
        ("  Yaad rakho: floor ek wada nahi hai, woh toot bhi sakta hai.", "orange", False),
        ("  Sirf seekhne ke liye. SEBI-registered advice nahi.", "dim", False),
    ]),
]
BARS = {1: (11.5, "green"), 2: (50.0, "red"), 3: (38.6, "dim")}   # scene 2 (Odds) line index -> bar


def keyframes(name, start, end, total):
    """Visible from start to end seconds within a loop of `total` seconds."""
    a, b = start / total * 100, end / total * 100
    fade = 0.6 / total * 100
    pts = [(0, 0), (max(a, 0.001), 0), (a + fade, 1), (b - fade, 1), (b, 0), (100, 0)]
    if a == 0:
        pts = [(0, 0), (fade, 1), (b - fade, 1), (b, 0), (100, 0)]
    body = " ".join("%.3f%%{opacity:%d}" % (p, o) for p, o in pts)
    return "@keyframes %s{%s}" % (name, body)


def main():
    total = SCENE * len(SCENES)
    css = [".t{font:15px 'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace;white-space:pre}",
           ".b{font-weight:700}", ".lbl{font:600 13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif}"]
    parts = []
    for i, (label, prompt, lines) in enumerate(SCENES):
        s0 = i * SCENE
        css.append(keyframes("p%d" % i, s0, s0 + SCENE, total))
        css.append(keyframes("o%d" % i, s0 + 1.1, s0 + SCENE, total))
        css.append(keyframes("l%d" % i, s0, s0 + SCENE, total))
        css.append(".p%d{opacity:0;animation:p%d %gs linear infinite}" % (i, i, total))
        css.append(".o%d{opacity:0;animation:o%d %gs linear infinite}" % (i, i, total))
        css.append(".l%d{opacity:0;animation:l%d %gs linear infinite}" % (i, i, total))
        g = ['<g class="p%d">' % i,
             '<text class="t" x="%d" y="%d" fill="%s">&gt; <tspan fill="%s">%s</tspan></text>' % (
                 X0, Y0, C["dim"], C["white"], escape(prompt)), '</g>', '<g class="o%d">' % i]
        for j, (text, colour, bold) in enumerate(lines):
            y = Y0 + 40 + j * LINE_H
            g.append('<text class="t%s" x="%d" y="%d" fill="%s">%s</text>' % (
                " b" if bold else "", X0, y, C[colour], escape(text)))
            if label == "Odds" and j in BARS:
                pctv, col = BARS[j]
                g.append('<rect x="%d" y="%d" width="%.1f" height="12" rx="3" fill="%s" opacity="0.85"/>' % (
                    X0 + 250, y - 11, pctv / 100 * 360, C[col]))
                if j == 3:
                    g.append('<text class="t" x="%d" y="%d" fill="%s">still open at 15:20</text>' % (
                        X0 + 250 + pctv / 100 * 360 + 14, y, C["dim"]))
        g.append('</g>')
        parts.append("\n".join(g))

    tabs = []
    tx = 28
    for i, (label, _, _) in enumerate(SCENES):
        w = 18 + len(label) * 8
        tabs.append('<g><rect x="%d" y="%d" width="%d" height="26" rx="13" fill="#21262D"/>'
                    '<text class="lbl" x="%d" y="%d" fill="%s">%d · %s</text>'
                    '<g class="l%d"><rect x="%d" y="%d" width="%d" height="26" rx="13" fill="#D97757"/>'
                    '<text class="lbl" x="%d" y="%d" fill="#fff">%d · %s</text></g></g>' % (
                        tx, H - 44, w + 24, tx + 12, H - 26, C["dim"], i + 1, label,
                        i, tx, H - 44, w + 24, tx + 12, H - 26, i + 1, label))
        tx += w + 34

    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Demo: Claude scans the Nifty 50, plans a TITAN trade with Indian charges, runs the Time Machine, and explains Jio's chart in Hinglish">
<style>{css}</style>
<rect width="{W}" height="{H}" rx="14" fill="#0D1117"/>
<rect width="{W}" height="44" rx="14" fill="#161B22"/>
<rect y="30" width="{W}" height="14" fill="#161B22"/>
<circle cx="24" cy="22" r="6" fill="#FF5F57"/><circle cx="44" cy="22" r="6" fill="#FEBC2E"/><circle cx="64" cy="22" r="6" fill="#28C840"/>
<text class="lbl" x="{cx}" y="27" text-anchor="middle" fill="#8B949E">Claude Code · dalal-street-skill · NSE &amp; BSE</text>
<rect x="0" y="44" width="{W}" height="3" fill="#FF9933"/><rect x="{w3}" y="44" width="{w3}" height="3" fill="#F4F6FA"/><rect x="{w23}" y="44" width="{w3r}" height="3" fill="#22B04B"/>
{parts}
<line x1="20" y1="{ly}" x2="{lx}" y2="{ly}" stroke="#21262D"/>
{tabs}
<text class="lbl" x="{rx}" y="{ty}" text-anchor="end" fill="#6E7681">Real NSE data · 29 Oct 2026 · paper trading only</text>
</svg>
""".format(W=W, H=H, css="".join(css), cx=W // 2, w3=W // 3, w23=2 * W // 3, w3r=W - 2 * W // 3,
           parts="\n".join(parts), ly=H - 58, lx=W - 20, tabs="\n".join(tabs), rx=W - 24, ty=H - 26)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.svg")
    with open(out, "w") as f:
        f.write(svg)
    print("wrote %s (%d bytes, %gs loop)" % (out, len(svg), total))


if __name__ == "__main__":
    main()
