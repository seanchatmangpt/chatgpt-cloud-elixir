"""Policy-example court: the committed least-privilege example must load and hold fences.

Guards local-control/policy.example.json against silent privilege creep:
- read-only operation set (an empty/missing allowed_operations would fall back to
  the agent's FULL DEFAULT_OPERATIONS set — this court pins the explicit set);
- empty write_roots denies all writes (Policy.require_write_path refuses when the
  list is empty);
- destructive stays disabled;
- transport repo/branch match the local-control-bus contract;
- every placeholder is clearly marked.
"""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "local_control_agent.py"
SPEC = importlib.util.spec_from_file_location("local_control_agent_policy", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)

EXAMPLE = Path(__file__).resolve().parents[1] / "local-control" / "policy.example.json"

READ_ONLY_OPERATIONS = {"system.snapshot", "filesystem.list", "filesystem.read"}


def load_example_policy():
    return mod.Policy.load(EXAMPLE)


def request(operation, payload=None, machine="*"):
    return {
        "request_id": "policy-court-1",
        "operation": operation,
        "machine": {"id": machine},
        "payload": payload or {},
    }


class PolicyExampleLoadTests(unittest.TestCase):
    def test_example_loads_via_policy_loader(self):
        policy = load_example_policy()
        self.assertIsInstance(policy, mod.Policy)

    def test_example_is_valid_json_with_only_placeholder_markers(self):
        raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(raw["machine_id"], "REPLACE_WITH_HOSTNAME")
        self.assertTrue(raw["_README"].strip())

    def test_allowed_operations_is_exact_read_only_set(self):
        policy = load_example_policy()
        self.assertEqual(policy.allowed_operations, READ_ONLY_OPERATIONS)

    def test_no_write_process_or_macos_operations_admitted(self):
        policy = load_example_policy()
        forbidden = {
            "filesystem.write",
            "filesystem.mkdir",
            "filesystem.delete",
            "process.run",
            "macos.open",
            "macos.notify",
            "macos.applescript.named",
        }
        self.assertEqual(policy.allowed_operations & forbidden, set())

    def test_transport_contract_repo_and_branch(self):
        policy = load_example_policy()
        self.assertEqual(policy.repo, "seanchatmangpt/chatgpt-cloud-elixir")
        self.assertEqual(policy.branch, "local-control-bus")

    def test_destructive_disabled(self):
        policy = load_example_policy()
        self.assertFalse(policy.allow_destructive)

    def test_write_roots_empty_denies_all_writes(self):
        policy = load_example_policy()
        self.assertEqual(policy.write_roots, [])
        with self.assertRaises(mod.Refused) as ctx:
            policy.require_write_path(Path(tempfile.gettempdir()) / "anywhere")
        self.assertEqual(ctx.exception.reason, "WRITE_PATH_NOT_ALLOWED")

    def test_read_roots_are_placeholders_under_home(self):
        policy = load_example_policy()
        self.assertTrue(policy.read_roots)
        home = Path(os.path.expandvars(os.path.expanduser("$HOME"))).resolve()
        for root in policy.read_roots:
            self.assertTrue(
                str(root).startswith(str(home) + os.sep),
                "read root %s is not scoped under $HOME" % root,
            )
            self.assertIn("REPLACE_WITH", str(root), "read root %s is not marked as placeholder" % root)

    def test_conservative_ceilings(self):
        policy = load_example_policy()
        self.assertEqual(policy.max_timeout_seconds, 120)
        self.assertEqual(policy.max_output_bytes, 65536)

    def test_no_executables_apps_or_applescripts_admitted(self):
        policy = load_example_policy()
        self.assertEqual(policy.allowed_executables, set())
        self.assertEqual(policy.allowed_apps, set())
        self.assertEqual(policy.named_applescripts, {})
        self.assertFalse(policy.raw.get("allow_open_urls", True))


class PolicyExampleFenceTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_example_policy()
        self.executor = mod.LocalExecutor(self.policy)

    def test_destructive_operation_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(request("filesystem.delete", {"path": "/tmp/anything"}))
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")

    def test_write_operation_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(
                request("filesystem.write", {"path": "/tmp/anything", "content": "x"})
            )
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")

    def test_mkdir_operation_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(request("filesystem.mkdir", {"path": "/tmp/anything"}))
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")

    def test_process_run_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(request("process.run", {"argv": ["git", "status"]}))
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")

    def test_read_outside_read_roots_refused(self):
        outside = tempfile.mkdtemp(prefix="policy-court-outside-")
        try:
            with self.assertRaises(mod.Refused) as ctx:
                self.executor.execute(request("filesystem.read", {"path": outside}))
            self.assertEqual(ctx.exception.reason, "READ_PATH_NOT_ALLOWED")
        finally:
            os.rmdir(outside)

    def test_read_outside_even_when_under_home_but_not_in_roots(self):
        home = Path(os.path.expandvars(os.path.expanduser("$HOME"))).resolve()
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(request("filesystem.read", {"path": str(home)}))
        self.assertEqual(ctx.exception.reason, "READ_PATH_NOT_ALLOWED")

    def test_unknown_operation_refused(self):
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(request("filesystem.delete_everything", {}))
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")

    def test_allowed_but_unimplemented_operation_refused(self):
        synthetic = mod.Policy(dict(self.policy.raw, allowed_operations=["time.travel"]))
        with self.assertRaises(mod.Refused) as ctx:
            mod.LocalExecutor(synthetic).execute(request("time.travel", {}))
        self.assertEqual(ctx.exception.reason, "UNSUPPORTED_OPERATION")


if __name__ == "__main__":
    unittest.main()
