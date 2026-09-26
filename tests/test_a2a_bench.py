"""Regression bounds for the A2A bus benchmark (scripts/bench_a2a.py).

The bound is on git process count, which is exact on any host: a sync must cost a
constant number of git processes, independent of how many messages the bus holds.
Before the batched/cached reader, a cold sync of N messages spawned N+6 processes
and a warm poll re-read every blob (receipt: a2a/receipts/*-harden-bench.receipt.json).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bench_a2a", ROOT / "scripts" / "bench_a2a.py")
bench = importlib.util.module_from_spec(SPEC)
sys.modules["bench_a2a"] = bench
SPEC.loader.exec_module(bench)

COLD_MAX, WARM_MAX, INCREMENTAL_MAX = 10, 4, 9


class BenchRegressionTest(unittest.TestCase):
    def test_sync_git_processes_do_not_grow_with_the_ledger(self) -> None:
        small = bench.run(ROOT / "scripts" / "a2a.py", 20)
        large = bench.run(ROOT / "scripts" / "a2a.py", 120)
        for result in (small, large):
            self.assertLessEqual(result["sync_cold"]["git_processes"], COLD_MAX, result)
            self.assertLessEqual(result["sync_warm"]["git_processes"], WARM_MAX, result)
            self.assertLessEqual(result["sync_incremental"]["git_processes"], INCREMENTAL_MAX, result)
        # O(1) in N: six times the messages, the same process count.
        self.assertEqual(small["sync_cold"]["git_processes"], large["sync_cold"]["git_processes"])
        self.assertEqual(small["sync_warm"]["git_processes"], large["sync_warm"]["git_processes"])

    def test_verify_chain_throughput_floor(self) -> None:
        result = bench.run(ROOT / "scripts" / "a2a.py", 60)
        # Measured ~98k msgs/s on the recording host; the floor only catches order-of-magnitude regressions.
        self.assertGreater(result["verify_chain"]["messages_per_second"], 2000, result)


if __name__ == "__main__":
    unittest.main()
