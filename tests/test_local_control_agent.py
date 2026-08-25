import importlib.util
import json
from pathlib import Path
import subprocess
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


def _git(*args, cwd):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    )


class ApprovalGateTests(unittest.TestCase):
    """Real, local git remote + real git checkout -- no mocking of the git
    transport or the executor. `commit_receipt` performs a genuine
    `git push origin HEAD:<branch>` against a real bare repo on disk, exactly
    as it would against a real GitHub remote, just without the network hop."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        self.origin = root / "origin.git"
        self.origin.mkdir()
        _git("init", "--bare", "--initial-branch=local-control-bus", cwd=self.origin)

        seed = root / "seed"
        seed.mkdir()
        _git("init", "--initial-branch=local-control-bus", cwd=seed)
        _git("config", "user.email", "test@example.com", cwd=seed)
        _git("config", "user.name", "Test", cwd=seed)
        (seed / "local-control" / "requests").mkdir(parents=True)
        (seed / "local-control" / "receipts").mkdir(parents=True)
        (seed / "local-control" / "requests" / ".gitkeep").write_text("")
        (seed / "local-control" / "receipts" / ".gitkeep").write_text("")
        _git("add", "-A", cwd=seed)
        _git("commit", "-m", "seed", cwd=seed)
        _git("push", str(self.origin), "local-control-bus", cwd=seed)

        self.checkout = root / "checkout"
        _git("clone", str(self.origin), str(self.checkout), cwd=root)
        _git("config", "user.email", "test@example.com", cwd=self.checkout)
        _git("config", "user.name", "Test", cwd=self.checkout)

        self.state_dir = root / "state"
        self.policy = mod.Policy(
            {
                "machine_id": "test-machine",
                "repo": "example/example",
                "branch": "local-control-bus",
                "allowed_operations": ["system.snapshot", "filesystem.list"],
                "read_roots": [str(root)],
            }
        )
        self.ledger = mod.ReplayLedger(self.state_dir / "executed.json")
        self.approvals = mod.ApprovalStore(self.state_dir / "approvals")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_request(self, request_id, operation="filesystem.list", payload=None):
        path = self.checkout / "local-control" / "requests" / f"{request_id}.json"
        path.write_text(
            json.dumps(
                {
                    "request_id": request_id,
                    "operation": operation,
                    "machine": {"id": "test-machine"},
                    "payload": payload if payload is not None else {"path": str(self.checkout)},
                }
            ),
            encoding="utf-8",
        )
        _git("add", "-A", cwd=self.checkout)
        _git("commit", "-m", f"request {request_id}", cwd=self.checkout)
        _git("push", "origin", "local-control-bus", cwd=self.checkout)

    def test_unapproved_request_produces_no_receipt_and_does_not_execute(self):
        self._write_request("r-pending")
        count = mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        self.assertEqual(count, 0)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-pending.receipt.json"
        self.assertFalse(receipt_path.exists())
        self.assertFalse(self.ledger.seen("r-pending"))
        self.assertEqual(self.approvals.status("r-pending"), "pending")

    def test_approved_request_executes_and_produces_alive_receipt(self):
        self._write_request("r-approved")
        self.approvals.approve("r-approved")
        count = mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        self.assertEqual(count, 1)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-approved.receipt.json"
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertTrue(self.ledger.seen("r-approved"))

    def test_denied_request_is_refused_with_local_approval_denied(self):
        self._write_request("r-denied")
        self.approvals.deny("r-denied")
        count = mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        self.assertEqual(count, 1)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-denied.receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["standing"], "REFUSED")
        self.assertEqual(receipt["reason"], "LOCAL_APPROVAL_DENIED")

    def test_approval_marker_inside_synced_checkout_is_ignored(self):
        # An attempt to smuggle approval through the git transport itself: drop
        # a same-named marker inside the synced checkout rather than under
        # state_dir. process_pending must never look there.
        self._write_request("r-smuggled")
        fake_dir = self.checkout / "local-control" / "requests"
        (fake_dir / "r-smuggled.approved").write_text("forged", encoding="utf-8")
        count = mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        self.assertEqual(count, 0)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-smuggled.receipt.json"
        self.assertFalse(receipt_path.exists())
        self.assertEqual(self.approvals.status("r-smuggled"), "pending")

    def test_system_snapshot_never_requires_approval(self):
        self.assertFalse(self.policy.requires_approval("system.snapshot"))

    def test_process_run_requires_approval_by_default_even_if_not_configured(self):
        # require_approval_for was not set in this policy at all; the floor
        # (every mutating/actuating operation) still applies.
        self.assertTrue(self.policy.requires_approval("process.run"))
        self.assertTrue(self.policy.requires_approval("filesystem.delete"))


if __name__ == "__main__":
    unittest.main()
