import importlib.util
import json
from pathlib import Path
import tempfile
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

    def req(self, operation, payload=None, machine="test-machine"):
        return {
            "request_id": "r1",
            "operation": operation,
            "machine": {"id": machine},
            "payload": payload or {},
        }

    def test_machine_scope_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(self.req("system.snapshot", machine="other"))
        self.assertEqual(ctx.exception.reason, "MACHINE_SCOPE_VIOLATION")

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

    def test_delete_disabled(self):
        target = self.write_root / "delete.txt"
        target.write_text("x", encoding="utf-8")
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(self.req("filesystem.delete", {"path": str(target)}))
        self.assertEqual(ctx.exception.reason, "DESTRUCTIVE_OPERATION_DISABLED")

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

    def test_expired_request_refused(self):
        req = self.req("system.snapshot")
        req["expires_at"] = "2000-01-01T00:00:00Z"
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(req)
        self.assertEqual(ctx.exception.reason, "REQUEST_EXPIRED")

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


if __name__ == "__main__":
    unittest.main()
