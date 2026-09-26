"""Regression bounds for the relay benchmark (scripts/bench_xaas_relay.py).

Bounds are on exact, host-independent counts: duplicate delivery spawns the
gall-work peer exactly once, refusals spawn nothing, and persisted relay state
is O(dedup_limit), not O(commands). Wall-time floors only catch order-of-
magnitude regressions (recorded numbers: verification/receipts/relay/).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bench_xaas_relay", ROOT / "scripts" / "bench_xaas_relay.py")
bench = importlib.util.module_from_spec(SPEC)
sys.modules["bench_xaas_relay"] = bench
SPEC.loader.exec_module(bench)

MODULE = ROOT / "scripts" / "xaas-relay.py"
ADMISSION_FLOOR = 5_000          # envelopes/s; recorded ~138k/s
REPLAY_MEDIAN_CEILING = 0.05     # seconds; recorded ~4.4e-5 s


class RelayBenchRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.small = bench.run(MODULE, commands=12, duplicates=60, dedup_limit=4, admissions=5000)
        cls.large = bench.run(MODULE, commands=36, duplicates=60, dedup_limit=4, admissions=5000)

    def test_duplicate_delivery_spawns_exactly_once(self):
        for result in (self.small, self.large):
            dup = result["duplicate_delivery"]
            self.assertEqual(dup["first_reason"], "EXECUTED_RECEIPTED")
            self.assertEqual(dup["replay_reasons"], ["KNOWN_REPLAY"])
            self.assertEqual(dup["spawns"], 1, dup)

    def test_refusals_never_spawn(self):
        for result in (self.small, self.large):
            ref = result["refusal"]
            self.assertEqual(ref["reasons"], ["REPLAY_IDENTITY_MISMATCH", "SEQUENCE_GAP"])
            self.assertEqual(ref["spawns_after"], 1, ref)

    def test_state_is_bounded_by_dedup_limit_not_commands(self):
        small, large = self.small["ordered_stream"], self.large["ordered_stream"]
        for stream in (small, large):
            self.assertEqual(stream["reasons"], ["EXECUTED_RECEIPTED"])
            self.assertEqual(stream["spawns"], stream["commands"])
            self.assertEqual(stream["last_acknowledged_sequence"], stream["commands"])
            self.assertEqual(stream["result_rows"], 4)
            self.assertEqual(stream["seen_ids"], 4)
        # 3x the commands: the persisted state grows only by id-width digits.
        self.assertLessEqual(large["state_bytes"], small["state_bytes"] + 64, (small, large))

    def test_admission_and_replay_latency_floors(self):
        self.assertGreater(self.small["admission"]["envelopes_per_second"], ADMISSION_FLOOR)
        self.assertLess(self.small["duplicate_delivery"]["replay_median_seconds"], REPLAY_MEDIAN_CEILING)


if __name__ == "__main__":
    unittest.main()
