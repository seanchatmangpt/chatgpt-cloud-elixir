import ast
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xaas_relay", ROOT / "scripts" / "xaas-relay.py")
relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relay)

CONTRACT = json.loads((ROOT / "contracts" / "xaas-remote-relay.contract.json").read_text())


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.worktree = self.root / "worktree"
        self.worktree.mkdir()
        self.state = self.root / "state.json"
        self.counter = self.root / "count.txt"
        self.zcode = self.root / "zcode"
        self.zcode.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib\n"
            "p=pathlib.Path(os.environ['COUNTER'])\n"
            "n=int(p.read_text())+1 if p.exists() else 1\n"
            "p.write_text(str(n))\n"
            "print(json.dumps({'schema':'gall.work-result/1','standing':'ALIVE','epoch_id':'11111111-1111-4111-8111-111111111111','outcome':'alive','final_head':'a'*40,'runtime_exit_code':0,'work_order_iri':os.environ.get('XAAS_WORK_ORDER_IRI'),'base_sha':os.environ.get('XAAS_BASE_SHA')}))\n"
        )
        self.zcode.chmod(self.zcode.stat().st_mode | stat.S_IXUSR)

    def descriptor(self):
        return {
            "schema": "gall.work-lease/1",
            "work_order_iri": "urn:work:1",
            "checkpoint_iri": "urn:checkpoint:1",
            "graph_digest": "sha256:" + "b" * 64,
            "repository_identity": "owner/repo",
            "base_sha": "a" * 40,
            "epoch_id": "11111111-1111-4111-8111-111111111111",
            "worker_id": "worker-1",
            "worktree": str(self.worktree),
        }

    def run_descriptor_case(self, **kwargs):
        # Never name this helper `run`: that shadows unittest.TestCase.run, so the
        # unittest runner's run(result) call raises TypeError and pytest skips
        # setUp; no relay test body executes under either runner.
        # TestCaseProtocolGuardTests below refuses that regression.
        env = dict(os.environ)
        env["COUNTER"] = str(self.counter)
        return relay.run_descriptor(
            self.descriptor(),
            state_path=self.state,
            manifest_digest=kwargs.pop("manifest_digest", "manifest-1"),
            zcode=str(self.zcode),
            env=env,
            **kwargs,
        )

    def envelope(self, **overrides):
        descriptor = self.descriptor()
        value = {
            "schema": "xaas.remote-relay-envelope/1",
            "command_id": "cmd-1",
            "epoch_id": descriptor["epoch_id"],
            "task_id": descriptor["work_order_iri"],
            "sequence": 1,
            "intent_digest": descriptor["graph_digest"],
            "exact_subject": f"{descriptor['repository_identity']}@{descriptor['base_sha']}",
            "verb": "actuate",
            "issued_at": 1,
            "expires_at": 10_000,
            "execution_manifest_digest": "manifest-1",
            "authority_ref": "grant-1",
            "channel": "control",
            "payload": descriptor,
        }
        value.update(overrides)
        return value

    def run_envelope(self, envelope=None, **kwargs):
        env = dict(os.environ)
        env["COUNTER"] = str(self.counter)
        return relay.run_envelope(
            envelope or self.envelope(),
            state_path=self.state,
            manifest_digest=kwargs.pop("manifest_digest", "manifest-1"),
            zcode=str(self.zcode),
            env=env,
            now_ms=kwargs.pop("now_ms", 5),
            **kwargs,
        )

    def test_shared_contract_pins_worker_admission_vocabulary(self):
        self.assertEqual(CONTRACT["contract"], "xaas-remote-relay")
        self.assertEqual(CONTRACT["contract_version"], 1)
        self.assertEqual(CONTRACT["envelope_schema"], relay.ENVELOPE_SCHEMA)
        self.assertEqual(
            CONTRACT["gall_work_binding"]["intent_digest"],
            "payload.graph_digest",
        )
        self.assertIn("AUTHORITY_REF_REQUIRED", CONTRACT["refusals"])
        self.assertIn("SEQUENCE_GAP", CONTRACT["refusals"])
        self.assertIn("KNOWN_REPLAY", CONTRACT["replay"]["after_ack"])
        self.assertEqual(
            CONTRACT["ocel_identity_env"],
            [
                "XAAS_LEASE_CWD",
                "XAAS_WORK_ORDER_IRI",
                "XAAS_EPOCH_ID",
                "XAAS_BASE_SHA",
            ],
        )

    def test_relay_envelope_executes_once_then_known_replay(self):
        first = self.run_envelope(allow_do=True)
        self.assertEqual(first["standing"], "ALIVE")
        self.assertEqual(first["reason"], "EXECUTED_RECEIPTED")
        self.assertTrue(first["executed"])
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(first["authority_ref"], "grant-1")
        self.assertEqual(first["result"]["work_order_iri"], "urn:work:1")
        self.assertEqual(first["result"]["base_sha"], "a" * 40)
        self.assertEqual(first["result"]["epoch_id"], "11111111-1111-4111-8111-111111111111")
        self.assertEqual(self.counter.read_text(), "1")

        second = self.run_envelope(allow_do=True)
        self.assertEqual(second["standing"], "ALIVE")
        self.assertEqual(second["reason"], "KNOWN_REPLAY")
        self.assertFalse(second["executed"])
        self.assertEqual(self.counter.read_text(), "1")

    def test_relay_envelope_preserves_double_authority_gate(self):
        row = self.run_envelope(allow_do=False)
        self.assertEqual(row["standing"], "REFUSED_AUTHORITY")
        self.assertEqual(row["reason"], "EXPLICIT_DO_ACK_REQUIRED")
        self.assertFalse(row["executed"])
        self.assertFalse(self.counter.exists())

        missing = self.envelope(authority_ref=None)
        row = self.run_envelope(missing, allow_do=True)
        self.assertEqual(row["standing"], "REFUSED")
        self.assertEqual(row["reason"], "AUTHORITY_REF_REQUIRED")
        self.assertFalse(row["executed"])
        self.assertFalse(self.counter.exists())

    def test_relay_envelope_refuses_manifest_drift_expiry_and_sequence_gap(self):
        drift = self.envelope(execution_manifest_digest="manifest-2")
        row = self.run_envelope(drift, allow_do=True)
        self.assertEqual(row["reason"], "EXECUTION_MANIFEST_DRIFT")
        self.assertFalse(row["executed"])

        expired = self.envelope(expires_at=4)
        row = self.run_envelope(expired, allow_do=True, now_ms=5)
        self.assertEqual(row["reason"], "COMMAND_EXPIRED")
        self.assertFalse(row["executed"])

        gap = self.envelope(command_id="cmd-2", sequence=2)
        row = self.run_envelope(gap, allow_do=True)
        self.assertEqual(row["reason"], "SEQUENCE_GAP")
        self.assertFalse(row["executed"])
        self.assertFalse(self.counter.exists())

    def test_relay_envelope_binds_semantic_identity(self):
        descriptor = self.descriptor()

        bad_intent = self.envelope(intent_digest="sha256:" + "0" * 64)
        self.assertEqual(
            self.run_envelope(bad_intent, allow_do=True)["reason"],
            "INTENT_DIGEST_MISMATCH",
        )

        bad_subject = self.envelope(exact_subject="owner/repo@" + "b" * 40)
        self.assertEqual(
            self.run_envelope(bad_subject, allow_do=True)["reason"],
            "EXACT_SUBJECT_MISMATCH",
        )

        bad_epoch = self.envelope(epoch_id="22222222-2222-4222-8222-222222222222")
        self.assertEqual(
            self.run_envelope(bad_epoch, allow_do=True)["reason"],
            "EPOCH_MISMATCH",
        )

        bad_task = self.envelope(task_id="urn:work:other")
        self.assertEqual(
            self.run_envelope(bad_task, allow_do=True)["reason"],
            "TASK_MISMATCH",
        )
        self.assertFalse(self.counter.exists())
        self.assertEqual(descriptor["work_order_iri"], "urn:work:1")

    def test_relay_envelope_requires_control_channel_for_actuation(self):
        row = self.run_envelope(
            self.envelope(channel="observe"),
            allow_do=True,
        )
        self.assertEqual(row["reason"], "AUTHORITY_REF_REQUIRED")
        self.assertFalse(row["executed"])
        self.assertFalse(self.counter.exists())

    def test_requires_explicit_local_do_ack(self):
        row = self.run_descriptor_case()
        self.assertEqual(row["standing"], "REFUSED_AUTHORITY")
        self.assertFalse(row["executed"])
        self.assertFalse(self.counter.exists())

    def test_success_is_durable_and_duplicate_replays_without_process(self):
        first = self.run_descriptor_case(allow_do=True)
        self.assertEqual(first["standing"], "ALIVE")
        self.assertTrue(first["executed"])
        self.assertEqual(self.counter.read_text(), "1")

        second = self.run_descriptor_case(allow_do=True)
        self.assertEqual(second["reason"], "KNOWN_REPLAY")
        self.assertFalse(second["executed"])
        self.assertEqual(second["result_digest"], first["result_digest"])
        self.assertEqual(self.counter.read_text(), "1")

    def test_manifest_drift_refuses_before_process(self):
        self.run_descriptor_case(allow_do=True)
        drift = self.run_descriptor_case(allow_do=True, manifest_digest="manifest-2")
        self.assertEqual(drift["reason"], "EXECUTION_MANIFEST_DRIFT")
        self.assertFalse(drift["executed"])
        self.assertEqual(self.counter.read_text(), "1")

    def test_descriptor_requires_exact_sha(self):
        bad = self.descriptor()
        bad["base_sha"] = "main"
        with self.assertRaisesRegex(ValueError, "DESCRIPTOR_BASE_SHA"):
            relay.validate_descriptor(bad)

    def test_state_dedup_is_bounded(self):
        state = relay.empty_state("manifest")
        state["seen_command_ids"] = ["a", "b"]
        relay.save_state(self.state, state)
        loaded = relay.load_state(self.state, "manifest")
        self.assertEqual(loaded["seen_command_ids"], ["a", "b"])


# TestCase protocol methods that a subclass must never redefine as helpers.
# Redefining any of these replaces the runner's entry point (TestCase.__call__
# -> TestCase.run -> setUp/test/tearDown), so tests appear to exist but never
# execute their bodies.
TESTCASE_PROTOCOL_METHODS = frozenset({"run", "__call__", "debug", "countTestCases", "id"})
TESTCASE_BASE_NAMES = frozenset({"TestCase", "IsolatedAsyncioTestCase"})
RELAY_TEST_FLOOR = 11


def _base_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def find_protocol_overrides(source, filename="<source>"):
    """Return (class, method, line) for TestCase subclasses shadowing runner protocol.

    TestCase ancestry is resolved transitively within the module, so a helper
    base class derived from unittest.TestCase is covered as well.
    """
    tree = ast.parse(source, filename=filename)
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    testcase_names = set(TESTCASE_BASE_NAMES)
    changed = True
    while changed:
        changed = False
        for cls in classes:
            if cls.name in testcase_names:
                continue
            if any(_base_name(base) in testcase_names for base in cls.bases):
                testcase_names.add(cls.name)
                changed = True
    findings = []
    for cls in classes:
        if cls.name not in testcase_names or cls.name in TESTCASE_BASE_NAMES:
            continue
        for item in cls.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                item.name in TESTCASE_PROTOCOL_METHODS
            ):
                findings.append((cls.name, item.name, item.lineno))
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in TESTCASE_PROTOCOL_METHODS:
                        findings.append((cls.name, target.id, item.lineno))
    return findings


class TestCaseProtocolGuardTests(unittest.TestCase):
    """Guards that the relay court suite actually executes (not merely loads)."""

    def test_no_testcase_under_tests_shadows_runner_protocol(self):
        findings = []
        for path in sorted((ROOT / "tests").glob("*.py")):
            for cls, method, line in find_protocol_overrides(path.read_text(), str(path)):
                findings.append(f"{path.relative_to(ROOT)}:{line} {cls}.{method}")
        self.assertEqual(findings, [], "TestCase subclasses shadow unittest protocol")

    def test_relay_suite_loads_and_executes_every_declared_test(self):
        declared = sorted(name for name in dir(RelayTests) if name.startswith("test"))
        self.assertGreaterEqual(len(declared), RELAY_TEST_FLOOR)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(RelayTests)
        self.assertEqual(suite.countTestCases(), len(declared))
        result = unittest.TestResult()
        suite.run(result)
        failures = [
            f"{test.id()}: {trace.splitlines()[-1]}"
            for test, trace in result.errors + result.failures
        ]
        self.assertEqual(failures, [])
        self.assertEqual(result.testsRun, len(declared))
        self.assertEqual(result.skipped, [])

    def test_court_command_form_resolves_repo_tests_package_and_runs_relay_suite(self):
        # Exact command form of remote-relay-live-leg.yml, executed as a real
        # subprocess from the repository root with the default site path.
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_xaas_relay.RelayTests"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        declared = len([name for name in dir(RelayTests) if name.startswith("test")])
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        self.assertIn(f"Ran {declared} tests", completed.stderr)
        self.assertTrue((ROOT / "tests" / "__init__.py").is_file())

    def test_scanner_flags_run_helper_on_direct_testcase(self):
        source = "import unittest\nclass T(unittest.TestCase):\n    def run(self, **kw):\n        pass\n"
        self.assertEqual(find_protocol_overrides(source), [("T", "run", 3)])

    def test_scanner_flags_call_async_and_assignment_forms(self):
        source = (
            "from unittest import TestCase, IsolatedAsyncioTestCase\n"
            "class A(TestCase):\n    def __call__(self):\n        pass\n"
            "class B(IsolatedAsyncioTestCase):\n    async def run(self):\n        pass\n"
            "class C(TestCase):\n    debug = None\n"
        )
        self.assertEqual(
            find_protocol_overrides(source),
            [("A", "__call__", 3), ("B", "run", 6), ("C", "debug", 9)],
        )

    def test_scanner_follows_transitive_testcase_bases(self):
        source = (
            "import unittest\n"
            "class Base(unittest.TestCase):\n    pass\n"
            "class Leaf(Base):\n    def id(self):\n        return 'x'\n"
        )
        self.assertEqual(find_protocol_overrides(source), [("Leaf", "id", 5)])

    def test_scanner_ignores_non_testcase_classes_and_module_functions(self):
        source = (
            "import unittest\n"
            "def run(**kw):\n    pass\n"
            "class Worker:\n    def run(self):\n        pass\n"
            "class T(unittest.TestCase):\n"
            "    def run_descriptor_case(self):\n        pass\n"
            "    def test_x(self):\n        def run():\n            pass\n"
        )
        self.assertEqual(find_protocol_overrides(source), [])


if __name__ == "__main__":
    unittest.main()
