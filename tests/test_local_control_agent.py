import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest import mock
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "local_control_agent.py"
SPEC = importlib.util.spec_from_file_location("local_control_agent", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


class LocalControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.read_root = root / "read"
        self.write_root = root / "write"
        self.read_root.mkdir()
        self.write_root.mkdir()
        self.policy = mod.Policy(
            {
                "machine_id": "test-machine",
                "allowed_operations": [
                    "system.snapshot",
                    "filesystem.list",
                    "filesystem.read",
                    "filesystem.write",
                    "filesystem.mkdir",
                    "filesystem.delete",
                    "process.run",
                ],
                "read_roots": [str(self.read_root), str(self.write_root)],
                "write_roots": [str(self.write_root)],
                "allowed_executables": ["python3"],
                "allow_destructive": False,
                "max_timeout_seconds": 5,
                "max_output_bytes": 4096,
            }
        )
        self.executor = mod.LocalExecutor(self.policy)

    def tearDown(self):
        self.tmp.cleanup()

    def req(self, operation, payload=None, machine="test-machine", **extra):
        envelope = {
            "request_id": "r1",
            "operation": operation,
            "machine": {"id": machine},
            "payload": payload or {},
        }
        envelope.update(extra)
        return envelope

    # ---- envelope / scope fencing -------------------------------------------------

    def test_machine_scope_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(self.req("system.snapshot", machine="other"))
        self.assertEqual(ctx.exception.reason, "MACHINE_SCOPE_VIOLATION")

    def test_unsupported_operation_refused_even_when_allowlisted(self):
        policy = mod.Policy(
            {
                "machine_id": "test-machine",
                "allowed_operations": ["totally.bogus"],
                "read_roots": [str(self.read_root)],
                "write_roots": [str(self.write_root)],
            }
        )
        with self.assertRaises(mod.Refused) as ctx:
            mod.LocalExecutor(policy).execute(self.req("totally.bogus"))
        self.assertEqual(ctx.exception.reason, "UNSUPPORTED_OPERATION")

    def test_operation_outside_policy_refused(self):
        policy = mod.Policy(
            {
                "machine_id": "test-machine",
                "allowed_operations": ["system.snapshot"],
                "read_roots": [str(self.read_root)],
                "write_roots": [str(self.write_root)],
            }
        )
        with self.assertRaises(mod.Refused) as ctx:
            mod.LocalExecutor(policy).execute(self.req("filesystem.delete", {"path": "/tmp/x"}))
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")

    def test_expired_request_refused(self):
        req = self.req("system.snapshot", expires_at="2000-01-01T00:00:00Z")
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(req)
        self.assertEqual(ctx.exception.reason, "REQUEST_EXPIRED")

    def test_expires_at_without_timezone_refused_not_build_broken(self):
        # A naive timestamp must be a typed refusal, never a BUILD_BROKEN leak.
        req = self.req("system.snapshot", expires_at="2000-01-01T00:00:00")
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(req)
        self.assertEqual(ctx.exception.reason, "INVALID_EXPIRES_AT")

    def test_expires_at_with_offset_and_future_date_allowed(self):
        req = self.req("system.snapshot", expires_at="2999-01-01T00:00:00+05:00")
        result = self.executor.execute(req)
        self.assertEqual(result["machine_id"], "test-machine")

    # ---- filesystem fencing -------------------------------------------------------

    def test_write_and_read_inside_roots(self):
        target = self.write_root / "a.txt"
        result = self.executor.execute(
            self.req("filesystem.write", {"path": str(target), "content": "hello"})
        )
        self.assertEqual(result["bytes"], 5)
        got = self.executor.execute(self.req("filesystem.read", {"path": str(target)}))
        self.assertEqual(got["content"], "hello")

    def test_write_outside_root_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(
                self.req(
                    "filesystem.write",
                    {"path": str(self.read_root / "x"), "content": "x"},
                )
            )
        self.assertEqual(ctx.exception.reason, "WRITE_PATH_NOT_ALLOWED")

    def test_list_outside_read_roots_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(self.req("filesystem.list", {"path": str(self.tmp.name)}))
        self.assertEqual(ctx.exception.reason, "READ_PATH_NOT_ALLOWED")

    def test_list_root_itself_is_inside_root(self):
        result = self.executor.execute(self.req("filesystem.list", {"path": str(self.read_root)}))
        self.assertEqual(Path(result["path"]), self.read_root.resolve())

    def test_list_regular_file_refused(self):
        target = self.read_root / "f.txt"
        target.write_text("x", encoding="utf-8")
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(self.req("filesystem.list", {"path": str(target)}))
        self.assertEqual(ctx.exception.reason, "NOT_A_DIRECTORY")

    def test_delete_disabled(self):
        target = self.write_root / "delete.txt"
        target.write_text("x", encoding="utf-8")
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(self.req("filesystem.delete", {"path": str(target)}))
        self.assertEqual(ctx.exception.reason, "DESTRUCTIVE_OPERATION_DISABLED")

    # ---- filesystem.read ceilings -------------------------------------------------

    def test_read_truncates_and_hashes_full_file(self):
        target = self.read_root / "big.txt"
        content = b"z" * 10240
        target.write_bytes(content)
        got = self.executor.execute(self.req("filesystem.read", {"path": str(target)}))
        self.assertTrue(got["truncated"])
        self.assertEqual(got["bytes_returned"], 4096)
        self.assertEqual(got["content"], "z" * 4096)
        self.assertEqual(got["sha256"], hashlib.sha256(content).hexdigest())

    def test_read_exact_cap_is_not_truncated(self):
        target = self.read_root / "exact.txt"
        content = b"y" * 4096
        target.write_bytes(content)
        got = self.executor.execute(self.req("filesystem.read", {"path": str(target)}))
        self.assertFalse(got["truncated"])
        self.assertEqual(got["bytes_returned"], 4096)
        self.assertEqual(got["sha256"], hashlib.sha256(content).hexdigest())

    def test_read_clamps_hostile_max_bytes(self):
        small = self.read_root / "small.txt"
        small.write_bytes(b"abcdef")
        negative = self.executor.execute(
            self.req("filesystem.read", {"path": str(small), "max_bytes": -10})
        )
        # A negative slice must never defeat the cap.
        self.assertEqual(negative["bytes_returned"], 1)
        self.assertTrue(negative["truncated"])
        big = self.read_root / "big.bin"
        big.write_bytes(b"b" * 8192)
        oversized = self.executor.execute(
            self.req("filesystem.read", {"path": str(big), "max_bytes": 999999})
        )
        # A hostile payload value cannot raise the ceiling above the policy cap.
        self.assertEqual(oversized["bytes_returned"], 4096)
        self.assertTrue(oversized["truncated"])
        self.assertEqual(oversized["sha256"], hashlib.sha256(b"b" * 8192).hexdigest())

    # ---- process.run fencing ------------------------------------------------------

    def test_process_run_allowlisted_without_shell(self):
        result = self.executor.execute(
            self.req(
                "process.run",
                {
                    "argv": ["python3", "-c", "print('alive')"],
                    "cwd": str(self.read_root),
                },
            )
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"].strip(), "alive")

    def test_process_run_non_allowlisted_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(
                self.req(
                    "process.run",
                    {"argv": ["sh", "-c", "echo no"], "cwd": str(self.read_root)},
                )
            )
        self.assertEqual(ctx.exception.reason, "EXECUTABLE_NOT_ALLOWED")

    def test_process_run_invalid_argv_refused(self):
        for bad in ([], ["python3", 1], "python3 -c 'x'"):
            with self.assertRaises(mod.Refused) as ctx:
                self.executor.execute(
                    self.req("process.run", {"argv": bad, "cwd": str(self.read_root)})
                )
            self.assertEqual(ctx.exception.reason, "INVALID_ARGV")

    def test_process_run_output_capped_at_pipe(self):
        # 2 MiB of stdout against a 4096-byte policy cap: the receipt keeps at
        # most the cap and reports truncation instead of buffering everything.
        result = self.executor.execute(
            self.req(
                "process.run",
                {
                    "argv": [
                        "python3",
                        "-c",
                        "import sys; sys.stdout.write('x' * 2097152)",
                    ],
                    "cwd": str(self.read_root),
                },
            )
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["stdout_truncated"])
        self.assertLessEqual(len(result["stdout"].encode("utf-8")), 4096)
        self.assertFalse(result["stderr_truncated"])

    def test_process_run_timeout_yields_process_timeout_receipt(self):
        root = Path(self.tmp.name)
        request_path = root / "r1.json"
        request_path.write_text(
            json.dumps(
                self.req(
                    "process.run",
                    {
                        "argv": ["python3", "-c", "import time; time.sleep(30)"],
                        "cwd": str(self.read_root),
                        "timeout_seconds": 1,
                    },
                )
            ),
            encoding="utf-8",
        )
        ledger = mod.ReplayLedger(root / "state" / "executed.json")
        receipt = mod.run_request(request_path, self.policy, ledger)
        self.assertEqual(receipt["standing"], "BUILD_BROKEN")
        self.assertEqual(receipt["reason"], "PROCESS_TIMEOUT")
        # Timeout is a terminal observation: a retry is a replay, not a rerun.
        with self.assertRaises(mod.Refused) as ctx:
            mod.run_request(request_path, self.policy, ledger)
        self.assertEqual(ctx.exception.reason, "REPLAY_DETECTED")

    def test_safe_env_drops_unlisted_variables(self):
        secret_key = "LOCAL_CONTROL_TEST_SECRET"
        os.environ[secret_key] = "leak-me"
        try:
            env = self.executor._safe_env()
        finally:
            os.environ.pop(secret_key, None)
        self.assertNotIn(secret_key, env)
        self.assertNotIn("PYTHONPATH", env)
        for kept in ("HOME", "PATH"):
            if kept in os.environ:
                self.assertIn(kept, env)

    # ---- macOS gating -------------------------------------------------------------

    def test_macos_operations_refused_off_darwin(self):
        policy = mod.Policy(
            {
                "machine_id": "test-machine",
                "allowed_operations": ["macos.notify"],
                "read_roots": [str(self.read_root)],
                "write_roots": [str(self.write_root)],
            }
        )
        with mock.patch.object(mod.platform, "system", return_value="Linux"):
            with self.assertRaises(mod.Refused) as ctx:
                mod.LocalExecutor(policy).execute(self.req("macos.notify", {"message": "hi"}))
        self.assertEqual(ctx.exception.reason, "UNSUPPORTED_PLATFORM")

    # ---- receipts + replay ledger -------------------------------------------------

    def test_receipt_shape(self):
        root = Path(self.tmp.name)
        request_path = root / "r1.json"
        request_path.write_text(json.dumps(self.req("system.snapshot")), encoding="utf-8")
        receipt = mod.run_request(request_path, self.policy, mod.ReplayLedger(root / "state" / "executed.json"))
        self.assertEqual(receipt["receipt_version"], 1)
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertEqual(receipt["request_id"], "r1")
        self.assertRegex(receipt["request_sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(receipt["completed_at"].endswith("Z"))
        self.assertIsNotNone(receipt["started_at"])
        self.assertIsNone(receipt["reason"])

    def test_receipt_and_replay_ledger(self):
        root = Path(self.tmp.name)
        request_path = root / "r1.json"
        request_path.write_text(json.dumps(self.req("system.snapshot")), encoding="utf-8")
        ledger = mod.ReplayLedger(root / "state" / "executed.json")
        receipt = mod.run_request(request_path, self.policy, ledger)
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertTrue(ledger.seen("r1"))
        with self.assertRaises(mod.Refused) as ctx:
            mod.run_request(request_path, self.policy, ledger)
        self.assertEqual(ctx.exception.reason, "REPLAY_DETECTED")

    def test_request_filename_is_part_of_authority(self):
        root = Path(self.tmp.name)
        request_path = root / "different.json"
        request_path.write_text(json.dumps(self.req("system.snapshot")), encoding="utf-8")
        ledger = mod.ReplayLedger(root / "state" / "executed.json")
        with self.assertRaises(mod.Refused) as ctx:
            mod.run_request(request_path, self.policy, ledger)
        self.assertEqual(ctx.exception.reason, "REQUEST_ID_PATH_MISMATCH")

    def test_replay_ledger_merges_concurrent_recorders(self):
        # Two agent processes holding the same ledger must not lose each
        # other's entries: each record re-reads on-disk state under a lock.
        root = Path(self.tmp.name)
        path = root / "state" / "executed.json"
        first = mod.ReplayLedger(path)
        second = mod.ReplayLedger(path)  # constructed before either records
        first.record("req-a", "a" * 64, "ALIVE")
        second.record("req-b", "b" * 64, "REFUSED")
        verifier = mod.ReplayLedger(path)
        self.assertTrue(verifier.seen("req-a"))
        self.assertTrue(verifier.seen("req-b"))
        self.assertTrue(first.seen("req-b"))
        with open(path, encoding="utf-8") as handle:
            on_disk = json.load(handle)
        self.assertEqual(
            sorted(on_disk["executed"]),
            ["req-a", "req-b"],
        )
        self.assertEqual(on_disk["executed"]["req-b"]["standing"], "REFUSED")

    def test_replay_ledger_preserves_request_sha256_and_standing(self):
        root = Path(self.tmp.name)
        path = root / "state" / "executed.json"
        ledger = mod.ReplayLedger(path)
        ledger.record("req-x", "c" * 64, "BUILD_BROKEN")
        with open(path, encoding="utf-8") as handle:
            entry = json.load(handle)["executed"]["req-x"]
        self.assertEqual(entry["request_sha256"], "c" * 64)
        self.assertEqual(entry["standing"], "BUILD_BROKEN")
        self.assertTrue(entry["recorded_at"].endswith("Z"))

    def test_process_pending_writes_refused_receipt_and_skips_seen(self):
        root = Path(self.tmp.name)
        checkout = root / "checkout"
        requests_dir = checkout / "local-control" / "requests"
        requests_dir.mkdir(parents=True)
        request_path = requests_dir / "r9.json"
        request_path.write_text(
            json.dumps(self.req("system.snapshot")), encoding="utf-8"
        )  # request_id r1 != file stem r9
        ledger = mod.ReplayLedger(root / "state" / "executed.json")
        with mock.patch.object(mod, "commit_receipt") as fake_commit:
            count = mod.process_pending(checkout, self.policy, ledger)
        self.assertEqual(count, 1)
        fake_commit.assert_called_once()
        receipt_path = checkout / "local-control" / "receipts" / "r9.receipt.json"
        with open(receipt_path, encoding="utf-8") as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["standing"], "REFUSED")
        self.assertEqual(receipt["reason"], "REQUEST_ID_PATH_MISMATCH")
        self.assertIsNotNone(receipt["request_sha256"])
        # A receipt on disk means the request is no longer pending.
        with mock.patch.object(mod, "commit_receipt") as fake_commit_again:
            self.assertEqual(mod.process_pending(checkout, self.policy, ledger), 0)
        fake_commit_again.assert_not_called()

    # ---- helpers ------------------------------------------------------------------

    def test_truncate_text_multibyte_boundary(self):
        value = "a" * 10 + "日" * 10
        truncated, flag = mod.truncate_text(value, 12)
        self.assertTrue(flag)
        # Truncation is byte-based; a glyph split across the limit degrades to
        # a replacement char (3 bytes), so the result may exceed the limit by
        # less than one glyph.
        self.assertLess(len(truncated.encode("utf-8")), 12 + 3)
        self.assertIn("\ufffd", truncated)
        exact, flag = mod.truncate_text("abcdef", 3)
        self.assertTrue(flag)
        self.assertEqual(exact, "abc")
        whole, flag = mod.truncate_text("short", 100)
        self.assertFalse(flag)
        self.assertEqual(whole, "short")

    def test_parse_utc_rejects_naive_timestamps(self):
        with self.assertRaises(ValueError):
            mod.parse_utc("2000-01-01T00:00:00")
        parsed = mod.parse_utc("2000-01-01T00:00:00Z")
        self.assertIsNotNone(parsed.tzinfo)


if __name__ == "__main__":
    unittest.main()
