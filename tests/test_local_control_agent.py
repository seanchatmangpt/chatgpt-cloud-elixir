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


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


class TrackBFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "work"
        self.repo.mkdir()
        git("init", "--initial-branch=main", cwd=self.repo)
        git("config", "user.email", "test@example.com", cwd=self.repo)
        git("config", "user.name", "Test", cwd=self.repo)
        git("remote", "add", "origin", "https://github.com/seanchatmangpt/chatgpt-cloud-elixir.git", cwd=self.repo)
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts" / "build-process-intelligence.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\necho build-evidence\necho verify-line >&2\n",
            encoding="utf-8",
        )
        (self.repo / "scripts" / "verify-process-intelligence.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\necho verify-evidence\n",
            encoding="utf-8",
        )
        (self.repo / "scripts" / "build-fail.sh").write_text(
            "#!/usr/bin/env bash\necho failed-build\nexit 7\n",
            encoding="utf-8",
        )
        git("add", "-A", cwd=self.repo)
        git("commit", "-m", "fixture", cwd=self.repo)

        self.fake_colima = self.root / "colima"
        self.fake_colima.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "[[ ${1:-} == ssh ]]\n"
            "[[ ${2:-} == -- ]]\n"
            "[[ ${3:-} == bash ]]\n"
            "[[ ${4:-} == -lc ]]\n"
            "exec bash -lc \"${5}\"\n",
            encoding="utf-8",
        )
        self.fake_colima.chmod(0o755)

        self.policy = mod.Policy(
            {
                "repo": "seanchatmangpt/chatgpt-cloud-elixir",
                "branch": "local-control-bus",
                "machine_id": "test-mac",
                "repo_root": str(self.repo),
                "allowed_operations": ["process.run"],
                "required_platform": "",
                "colima_executable": str(self.fake_colima),
                "max_timeout_seconds": 30,
                "max_output_bytes": 100000,
            }
        )
        self.state = self.root / "state"
        self.ledger = mod.ReplayLedger(self.state / "executed.json")
        self.approvals = mod.ApprovalStore(self.state / "approvals")

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, request_id="r1", script="scripts/build-process-intelligence.sh", **payload_extra):
        payload = {"script": script}
        payload.update(payload_extra)
        return {
            "request_id": request_id,
            "operation": "process.run",
            "machine": {"id": "test-mac"},
            "payload": payload,
        }

    def write_request(self, directory, request):
        path = Path(directory) / f"{request['request_id']}.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        return path


class AdmissionTests(TrackBFixture):
    def test_only_process_run_policy_is_allowed(self):
        with self.assertRaises(ValueError):
            mod.Policy(
                {
                    "repo_root": str(self.repo),
                    "required_platform": "",
                    "allowed_operations": ["process.run", "system.snapshot"],
                }
            )

    def test_build_and_verify_script_family_admitted(self):
        for script in (
            "scripts/build-process-intelligence.sh",
            "scripts/verify-process-intelligence.sh",
        ):
            path = self.write_request(self.root, self.request(script=script))
            admitted = mod.validate_request(path, self.policy, self.ledger)
            self.assertEqual(admitted["request"]["payload"]["script"], script)
            path.unlink()

    def test_arbitrary_shell_text_is_refused(self):
        request = self.request(script="scripts/build-process-intelligence.sh")
        request["payload"]["argv"] = ["bash", "-lc", "rm -rf ~"]
        path = self.write_request(self.root, request)
        with self.assertRaises(mod.Refused) as ctx:
            mod.validate_request(path, self.policy, self.ledger)
        self.assertEqual(ctx.exception.reason, "INVALID_PAYLOAD_FIELDS")

    def test_non_family_script_is_refused(self):
        path = self.write_request(self.root, self.request(script="scripts/project_memory_proxy.py"))
        with self.assertRaises(mod.Refused) as ctx:
            mod.validate_request(path, self.policy, self.ledger)
        self.assertEqual(ctx.exception.reason, "SCRIPT_NOT_ALLOWED")

    def test_wildcard_machine_is_refused(self):
        request = self.request()
        request["machine"] = {"id": "*"}
        path = self.write_request(self.root, request)
        with self.assertRaises(mod.Refused) as ctx:
            mod.validate_request(path, self.policy, self.ledger)
        self.assertEqual(ctx.exception.reason, "MACHINE_SCOPE_VIOLATION")

    def test_request_hash_binds_approval(self):
        request = self.request()
        path = self.write_request(self.root, request)
        admitted = mod.validate_request(path, self.policy, self.ledger)
        digest = admitted["request_sha256"]
        self.approvals.approve("r1", digest)
        self.assertEqual(self.approvals.status("r1", digest), "approved")
        request["payload"]["timeout_seconds"] = 2
        path.write_text(json.dumps(request), encoding="utf-8")
        changed = mod.validate_request(path, self.policy, self.ledger)["request_sha256"]
        self.assertNotEqual(changed, digest)
        self.assertEqual(self.approvals.status("r1", changed), "pending")

    def test_literal_command_is_locally_manufactured(self):
        path = self.write_request(self.root, self.request())
        admitted = mod.validate_request(path, self.policy, self.ledger)
        plan = mod.command_plan(admitted, self.policy)
        self.assertEqual(plan["argv"][0], str(self.fake_colima.resolve()))
        self.assertEqual(plan["argv"][1:5], ["ssh", "--", "bash", "-lc"])
        self.assertIn("exec bash ./scripts/build-process-intelligence.sh", plan["inner_command"])
        self.assertNotIn("argv", admitted["request"]["payload"])
        self.assertEqual(len(plan["script_sha256"]), 64)
        self.assertEqual(len(plan["repo"]["head_sha"]), 40)


class ExecutionTests(TrackBFixture):
    def test_success_receipt_embeds_real_output(self):
        path = self.write_request(self.root, self.request())
        admitted = mod.validate_request(path, self.policy, self.ledger)
        receipt = mod.execute_admitted(admitted, self.policy)
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertEqual(receipt["result"]["exit_code"], 0)
        self.assertIn("build-evidence", receipt["result"]["stdout"])
        self.assertIn("verify-line", receipt["result"]["stderr"])
        self.assertEqual(len(receipt["result"]["stdout_sha256"]), 64)
        self.assertIn("literal_command", receipt["command"])
        self.assertIn("head_sha", receipt["command"]["repo"])

    def test_nonzero_is_build_broken_with_output(self):
        path = self.write_request(self.root, self.request(script="scripts/build-fail.sh"))
        admitted = mod.validate_request(path, self.policy, self.ledger)
        receipt = mod.execute_admitted(admitted, self.policy)
        self.assertEqual(receipt["standing"], "BUILD_BROKEN")
        self.assertEqual(receipt["reason"], "PROCESS_EXIT_NONZERO")
        self.assertEqual(receipt["result"]["exit_code"], 7)
        self.assertIn("failed-build", receipt["result"]["stdout"])


class ApprovalTransportTests(TrackBFixture):
    def setUp(self):
        super().setUp()
        self.origin = self.root / "origin.git"
        self.origin.mkdir()
        git("init", "--bare", "--initial-branch=local-control-bus", cwd=self.origin)
        seed = self.root / "seed"
        seed.mkdir()
        git("init", "--initial-branch=local-control-bus", cwd=seed)
        git("config", "user.email", "test@example.com", cwd=seed)
        git("config", "user.name", "Test", cwd=seed)
        (seed / "local-control" / "requests").mkdir(parents=True)
        (seed / "local-control" / "receipts").mkdir(parents=True)
        (seed / "local-control" / "requests" / ".gitkeep").write_text("")
        (seed / "local-control" / "receipts" / ".gitkeep").write_text("")
        git("add", "-A", cwd=seed)
        git("commit", "-m", "seed", cwd=seed)
        git("push", str(self.origin), "local-control-bus", cwd=seed)
        self.checkout = self.root / "transport"
        git("clone", str(self.origin), str(self.checkout), cwd=self.root)
        git("config", "user.email", "test@example.com", cwd=self.checkout)
        git("config", "user.name", "Test", cwd=self.checkout)

    def add_transport_request(self, request):
        path = self.checkout / "local-control" / "requests" / f"{request['request_id']}.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        git("add", "-A", cwd=self.checkout)
        git("commit", "-m", f"request {request['request_id']}", cwd=self.checkout)
        git("push", "origin", "local-control-bus", cwd=self.checkout)
        return path

    def test_pending_receipt_is_persisted_before_execution(self):
        self.add_transport_request(self.request("r-pending"))
        changed = mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        self.assertEqual(changed, 1)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-pending.receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["standing"], "PENDING_APPROVAL")
        self.assertEqual(receipt["reason"], "LOCAL_APPROVAL_REQUIRED")
        self.assertIn("colima", receipt["command"]["literal_command"])
        self.assertFalse(self.ledger.seen("r-pending"))

    def test_approved_request_replaces_pending_receipt_with_alive(self):
        request = self.request("r-approved")
        self.add_transport_request(request)
        mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        pending_path = self.checkout / "local-control" / "receipts" / "r-approved.receipt.json"
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
        self.approvals.approve("r-approved", pending["request_sha256"])
        changed = mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        self.assertEqual(changed, 1)
        final = json.loads(pending_path.read_text(encoding="utf-8"))
        self.assertEqual(final["standing"], "ALIVE")
        self.assertIn("build-evidence", final["result"]["stdout"])
        self.assertTrue(self.ledger.seen("r-approved"))

    def test_denied_request_replaces_pending_with_refused(self):
        self.add_transport_request(self.request("r-denied"))
        mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-denied.receipt.json"
        pending = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.approvals.deny("r-denied", pending["request_sha256"])
        mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        final = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(final["standing"], "REFUSED")
        self.assertEqual(final["reason"], "LOCAL_APPROVAL_DENIED")

    def test_changed_request_invalidates_prior_approval(self):
        request = self.request("r-change")
        request_path = self.add_transport_request(request)
        mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        receipt_path = self.checkout / "local-control" / "receipts" / "r-change.receipt.json"
        first = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.approvals.approve("r-change", first["request_sha256"])

        request["payload"]["script"] = "scripts/verify-process-intelligence.sh"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        git("add", "-A", cwd=self.checkout)
        git("commit", "-m", "change pending request", cwd=self.checkout)
        git("push", "origin", "local-control-bus", cwd=self.checkout)

        mod.process_pending(self.checkout, self.policy, self.ledger, self.approvals)
        changed = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(changed["standing"], "PENDING_APPROVAL")
        self.assertNotEqual(changed["request_sha256"], first["request_sha256"])
        self.assertFalse(self.ledger.seen("r-change"))


if __name__ == "__main__":
    unittest.main()
