"""Offline checks for the India Trader skills (no internet needed).

  python3 tests/test_india_trader.py
"""
import datetime
import importlib.util
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HERE = os.path.join(ROOT, "nse-lib")
sys.path.insert(0, HERE)
import nselib as n  # noqa: E402


def load(skill, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, skill, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tm = load("nse-timemachine", "timemachine")


class Charges(unittest.TestCase):
    def test_trade_1_jio_stop(self):
        # Paper Trade #1: 66 JPL bought at 1,425, stopped at 1,410, intraday on NSE.
        c = n.charges(66 * 1425, 66 * 1410)
        self.assertEqual(c["brokerage"], 40.0)   # Rs 20 cap, each side
        self.assertEqual(c["stt"], 23.27)        # 0.025% of the sell
        self.assertEqual(c["stamp"], 2.82)       # 0.003% of the buy
        self.assertEqual(c["total"], 80.07)

    def test_small_order_minimum_brokerage(self):
        c = n.charges(1425, 1430)                # 1 share: 0.1% is Rs 1.43, the minimum is Rs 5
        self.assertEqual(c["brokerage"], 10.0)

    def test_delivery_has_dp_and_both_side_stt(self):
        c = n.charges(100000, 101000, kind="delivery")
        self.assertEqual(c["stt"], 201.0)
        self.assertEqual(c["dp"], 15.93)


class Formatting(unittest.TestCase):
    def test_rupees(self):
        self.assertEqual(n.rs(94050), "₹94,050")
        self.assertEqual(n.rs(1234567.5), "₹12,34,567.50")
        self.assertEqual(n.rs(-1070.07), "-₹1,070.07")
        self.assertEqual(n.rs(80, sign=True), "+₹80")


class Symbols(unittest.TestCase):
    def test_aliases_and_suffixes(self):
        self.assertEqual(n.to_yahoo("jio"), "JPL.NS")
        self.assertEqual(n.to_yahoo("RELIANCE", "BSE"), "RELIANCE.BO")
        self.assertEqual(n.to_yahoo("nifty"), "^NSEI")
        self.assertEqual(n.plain("TCS.NS"), "TCS")


class Clock(unittest.TestCase):
    def test_market_status(self):
        f = lambda s: n.market_status(n.now_ist(s))  # noqa: E731
        self.assertEqual(f("2026-10-29 09:05"), "pre-open")
        self.assertEqual(f("2026-10-29 12:10"), "open")
        self.assertEqual(f("2026-10-29 15:30"), "closed")
        self.assertEqual(f("2026-10-31 11:00"), "closed-weekend")   # a Saturday


class Levels(unittest.TestCase):
    def bars(self, lows):
        t0 = datetime.datetime(2026, 10, 29, 9, 15, tzinfo=n.IST)
        return [{"t": t0 + datetime.timedelta(minutes=5 * i), "o": l + 1, "h": l + 2, "l": l, "c": l + 1, "v": 100}
                for i, l in enumerate(lows)]

    def test_floor_with_two_touches(self):
        b = self.bars([105, 103, 100, 103, 106, 103, 100.1, 103, 105])
        floors, _ = n.levels(b, 104)
        self.assertEqual(floors[0]["touches"], 2)
        self.assertAlmostEqual(floors[0]["price"], 100.05)

    def test_opening_range(self):
        o = n.opening_range(self.bars([100, 98, 99, 101]))
        self.assertEqual((o["low"], o["high"], o["end"]), (98, 102, "09:30"))


class TimeMachine(unittest.TestCase):
    def test_both_touched_counts_as_stop(self):
        self.assertEqual(tm.walk([(100, 106, 94, 100)], 100, 95, 105)[0], "stop")

    def test_target_then_neither(self):
        self.assertEqual(tm.walk([(100, 101, 99, 100), (100, 105.5, 99.5, 105)], 100, 95, 105)[0], "target")
        self.assertEqual(tm.walk([(100, 101, 99, 100.5)], 100, 95, 105), ("neither", 100.5))

    def test_verdict_uses_break_even(self):
        # 2R: break-even is 33.3% of the replays that hit a side.
        self.assertTrue(tm.verdict(240, 505, 2.0).startswith("Close to break-even"))
        self.assertTrue(tm.verdict(115, 500, 2.0).startswith("Leans toward the stop"))
        self.assertTrue(tm.verdict(500, 500, 1.0).startswith("Close to a coin flip"))
        self.assertTrue(tm.verdict(800, 200, 1.0).startswith("Strongly toward the target"))

    def test_slots(self):
        self.assertEqual(tm.slot_of("09:15"), 0)
        self.assertEqual(tm.slot_of("15:20"), 73)
        self.assertEqual(tm.slot_time(74), "15:25")


if __name__ == "__main__":
    unittest.main(verbosity=2)
