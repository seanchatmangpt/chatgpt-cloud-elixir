"""Falsifier court for the bounded local-control agent (wave v26.9.23, slice S08).

Core invariant under permanent test here: NO falsified or out-of-policy request
may actuate. Every refusal must be typed AND non-actuating — the world must be
byte-for-byte unchanged by a refused request.

Each case asserts BOTH:
  1. the typed refusal (Refused.reason, or receipt standing REFUSED + reason), and
  2. that no mutation happened (files absent / untouched, ledger not advanced).

Anti-vacuity: wherever a gate is asserted, a "control" twin (same envelope minus
the offending field, or with the gate opened) is proven to actuate, so the gate
is load-bearing and the test cannot pass on a broken agent that refuses nothing.

Adversarial helper: envelopes are built and hashed with canonical JSON exactly
like the agent's sha256_json (sorted keys, tight separators), then one field is
mutated AFTER hashing. The court must (a) change its detection outcome on the
mutated envelope and (b) show a digest difference — a naive replayer that only
checks "is it JSON with a request_id" would actuate envelopes the court refuses.

Python 3.9 + 3.12+ compatible, stdlib only. Runs against the CURRENT agent and
documents present behavior; it does not modify the agent.
"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "local_control_agent.py"
SPEC = importlib.util.spec_from_file_location("local_control_agent", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)

MACHINE_ID = "court-machine"
FOREIGN_MACHINE = "some-other-laptop"
EXPIRED_AT = "2000-01-01T00:00:00Z"
FAR_FUTURE_AT = "2999-01-01T00:00:00Z"
ABSENT_EXECUTABLE = "lc26923-absent-binary-9f2e7"


def canonical_dumps(value):
    """Mirror of mod.canonical_json — the agent's seal is canonical JSON."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value):
    """Mirror of mod.sha256_json, computed independently of the agent."""
    return hashlib.sha256(canonical_dumps(value).encode("utf-8")).hexdigest()


def make_envelope(request_id, operation, machine_id=MACHINE_ID, payload=None, expires_at=None):
    envelope = {
        "request_id": request_id,
        "operation": operation,
        "machine": {"id": machine_id},
        "payload": payload if payload is not None else {},
    }
    if expires_at is not None:
        envelope["expires_at"] = expires_at
    return envelope


def naive_replayer_would_actuate(envelope):
    """Stand-in for a naive replayer: actuates any parseable envelope that
    carries a request_id, without scope/expiry/policy/hash examination."""
    return isinstance(envelope, dict) and bool(str(envelope.get("request_id", "")).strip())



def _ledger_executed(ledger):
    """Executed-entry snapshot via the public on-disk contract.

    An absent ledger file is the empty executed set (no admitted request
    has ever been recorded), not a missing court surface.
    """
    if not ledger.path.exists():
        return {}
    return json.loads(ledger.path.read_text(encoding="utf-8"))["executed"]


class LocalControlFalsifierCourt(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.read_root = root / "read"
        self.write_root = root / "write"
        self.outside = root / "outside"
        self.read_root.mkdir()
        self.write_root.mkdir()
        self.outside.mkdir()
        self.policy = self.make_policy()
        self.executor = mod.LocalExecutor(self.policy)

    def tearDown(self):
        self.tmp.cleanup()

    # --- construction helpers -------------------------------------------------

    def make_policy(self, **overrides):
        raw = {
            "machine_id": MACHINE_ID,
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
        raw.update(overrides)
        return mod.Policy(raw)

    def write_payload(self, tag, content="court-probe"):
        return {"path": str(self.write_root / (tag + ".txt")), "content": content}

    def run_envelope(self, envelope, policy=None):
        """Write the envelope to a temp request file (deliberately NON-canonical
        on-disk layout) and drive the agent's real run_request entrypoint.
        The stem always equals request_id unless a case is deliberately breaking
        that binding. One shared ReplayLedger per test, like a real state dir."""
        if not hasattr(self, "_ledger"):
            self._ledger = mod.ReplayLedger(Path(self.tmp.name) / "state" / "executed.json")
        path = Path(self.tmp.name) / (str(envelope["request_id"]) + ".json")
        path.write_text(json.dumps(envelope, indent=1), encoding="utf-8")
        return mod.run_request(path, policy or self.policy, self._ledger)

    def assertRefusedReceipt(self, receipt, reason):
        self.assertEqual(receipt["standing"], "REFUSED")
        self.assertEqual(receipt["reason"], reason)
        self.assertIsNone(receipt["result"])

    def assertAbsent(self, path):
        self.assertFalse(Path(path).exists(), "refused request must not create %s" % path)

    # --- 1. REQUEST_EXPIRED ---------------------------------------------------

    def test_expired_request_never_actuates(self):
        target = self.write_root / "expired.txt"
        envelope = make_envelope(
            "fals-01-expired",
            "filesystem.write",
            payload={"path": str(target), "content": "should never land"},
            expires_at=EXPIRED_AT,
        )
        # Executor level: typed refusal, no write.
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "REQUEST_EXPIRED")
        self.assertAbsent(target)
        # Receipt level: standing REFUSED with the typed reason.
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "REQUEST_EXPIRED")
        self.assertAbsent(target)
        # Anti-vacuity control: the identical envelope without expires_at actuates,
        # so the expiry gate — not something else — is what held.
        control = make_envelope(
            "fals-01-control",
            "filesystem.write",
            payload={"path": str(target), "content": "control"},
        )
        control_receipt = self.run_envelope(control)
        self.assertEqual(control_receipt["standing"], "ALIVE")
        self.assertTrue(target.exists())

    # --- 2. MACHINE_SCOPE_VIOLATION -------------------------------------------

    def test_machine_scope_violation_never_actuates(self):
        target = self.write_root / "foreign.txt"
        envelope = make_envelope(
            "fals-02-foreign",
            "filesystem.write",
            machine_id=FOREIGN_MACHINE,
            payload={"path": str(target), "content": "foreign"},
        )
        self.assertNotIn(FOREIGN_MACHINE, {MACHINE_ID, "*"})
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "MACHINE_SCOPE_VIOLATION")
        self.assertAbsent(target)
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "MACHINE_SCOPE_VIOLATION")
        self.assertAbsent(target)
        # Control: same envelope addressed to this machine actuates.
        control = make_envelope(
            "fals-02-control",
            "filesystem.write",
            payload={"path": str(target), "content": "local"},
        )
        self.assertEqual(self.run_envelope(control)["standing"], "ALIVE")
        self.assertTrue(target.exists())

    # --- 3. OPERATION_NOT_ALLOWED / UNSUPPORTED_OPERATION ---------------------

    def test_operation_not_allowed_never_actuates(self):
        victim = self.write_root / "keepme.txt"
        victim.write_text("precious", encoding="utf-8")
        tight = self.make_policy(allowed_operations=["system.snapshot", "filesystem.read"])
        envelope = make_envelope(
            "fals-03-noop",
            "filesystem.delete",
            payload={"path": str(victim)},
        )
        with self.assertRaises(mod.Refused) as ctx:
            mod.LocalExecutor(tight).execute(envelope)
        self.assertEqual(ctx.exception.reason, "OPERATION_NOT_ALLOWED")
        self.assertTrue(victim.exists())
        self.assertEqual(victim.read_text(encoding="utf-8"), "precious")
        receipt = self.run_envelope(envelope, policy=tight)
        self.assertRefusedReceipt(receipt, "OPERATION_NOT_ALLOWED")
        self.assertTrue(victim.exists())

    def test_unsupported_operation_never_actuates(self):
        # Operation is ALLOWED by policy but has no handler: must still be a
        # typed refusal, never a crash or a silent no-op receipt with ALIVE.
        loose = self.make_policy(allowed_operations=["ghost.op", "system.snapshot"])
        envelope = make_envelope("fals-04-ghost", "ghost.op")
        with self.assertRaises(mod.Refused) as ctx:
            mod.LocalExecutor(loose).execute(envelope)
        self.assertEqual(ctx.exception.reason, "UNSUPPORTED_OPERATION")
        receipt = self.run_envelope(envelope, policy=loose)
        self.assertRefusedReceipt(receipt, "UNSUPPORTED_OPERATION")
        self.assertEqual(_ledger_executed(self._ledger)["fals-04-ghost"]["standing"], "REFUSED")

    # --- 4. REPLAY_DETECTED ----------------------------------------------------

    def test_replay_detected_no_second_actuation(self):
        target = self.write_root / "once.txt"
        envelope = make_envelope(
            "fals-05-replay",
            "filesystem.write",
            payload={"path": str(target), "content": "first-and-only"},
        )
        first = self.run_envelope(envelope)
        self.assertEqual(first["standing"], "ALIVE")
        self.assertEqual(target.read_text(encoding="utf-8"), "first-and-only")
        self.assertEqual(len(_ledger_executed(self._ledger)), 1)
        # Same request file again: typed refusal, and the world did not move.
        with self.assertRaises(mod.Refused) as ctx:
            self.run_envelope(envelope)
        self.assertEqual(ctx.exception.reason, "REPLAY_DETECTED")
        self.assertEqual(target.read_text(encoding="utf-8"), "first-and-only")
        self.assertEqual(len(_ledger_executed(self._ledger)), 1)

    def test_replayed_id_with_mutated_content_is_refused(self):
        # Same request_id, different payload: a replayer keyed only on content
        # would run it again; the ledger is keyed on the id and must refuse.
        target = self.write_root / "immutable.txt"
        first_env = make_envelope(
            "fals-06-mutate-replay",
            "filesystem.write",
            payload={"path": str(target), "content": "v1"},
        )
        self.assertEqual(self.run_envelope(first_env)["standing"], "ALIVE")
        second_env = make_envelope(
            "fals-06-mutate-replay",
            "filesystem.write",
            payload={"path": str(target), "content": "v2"},
        )
        self.assertNotEqual(sha256_json(first_env), sha256_json(second_env))
        with self.assertRaises(mod.Refused) as ctx:
            self.run_envelope(second_env)
        self.assertEqual(ctx.exception.reason, "REPLAY_DETECTED")
        self.assertEqual(target.read_text(encoding="utf-8"), "v1")
        self.assertEqual(len(_ledger_executed(self._ledger)), 1)

    # --- 5. REQUEST_ID_PATH_MISMATCH -------------------------------------------

    def test_request_id_path_mismatch_never_actuates(self):
        target = self.write_root / "mismatch.txt"
        envelope = make_envelope(
            "fals-07-imposter",
            "filesystem.write",
            payload={"path": str(target), "content": "smuggled"},
        )
        # File stem deliberately differs from the embedded request_id.
        ledger = mod.ReplayLedger(Path(self.tmp.name) / "state" / "mismatch-ledger.json")
        path = Path(self.tmp.name) / "fals-07-different-stem.json"
        path.write_text(json.dumps(envelope), encoding="utf-8")
        with self.assertRaises(mod.Refused) as ctx:
            mod.run_request(path, self.policy, ledger)
        self.assertEqual(ctx.exception.reason, "REQUEST_ID_PATH_MISMATCH")
        self.assertAbsent(target)
        # The mismatched request never entered the ledger either.
        self.assertEqual(_ledger_executed(ledger), {})

    # --- 6. DESTRUCTIVE_OPERATION_DISABLED -------------------------------------

    def test_destructive_disabled_file_survives(self):
        victim = self.write_root / "survivor.txt"
        victim.write_text("still-here", encoding="utf-8")
        envelope = make_envelope(
            "fals-08-nodelete",
            "filesystem.delete",
            payload={"path": str(victim)},
        )
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "DESTRUCTIVE_OPERATION_DISABLED")
        self.assertTrue(victim.exists())
        self.assertEqual(victim.read_text(encoding="utf-8"), "still-here")
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "DESTRUCTIVE_OPERATION_DISABLED")
        self.assertTrue(victim.exists())
        # Control: with the gate opened, the same envelope deletes — the gate,
        # not the handler, is what saved the file.
        armed = self.make_policy(allow_destructive=True)
        control = make_envelope(
            "fals-08-control",
            "filesystem.delete",
            payload={"path": str(victim)},
        )
        result = mod.LocalExecutor(armed).execute(control)
        self.assertTrue(result["deleted"])
        self.assertFalse(victim.exists())

    # --- 7. READ_PATH_NOT_ALLOWED / WRITE_PATH_NOT_ALLOWED ---------------------

    def test_read_path_not_allowed(self):
        secret = self.outside / "secret.txt"
        secret.write_text(" classified ", encoding="utf-8")
        envelope = make_envelope(
            "fals-09-read-outside",
            "filesystem.read",
            payload={"path": str(secret)},
        )
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "READ_PATH_NOT_ALLOWED")
        # No mutation: the file is untouched and nothing leaked into the result.
        self.assertEqual(secret.read_text(encoding="utf-8"), " classified ")
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "READ_PATH_NOT_ALLOWED")

    def test_write_path_not_allowed_creates_nothing(self):
        outside_target = self.outside / "evil.txt"
        envelope = make_envelope(
            "fals-10-write-outside",
            "filesystem.write",
            payload={"path": str(outside_target), "content": "nope"},
        )
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "WRITE_PATH_NOT_ALLOWED")
        self.assertAbsent(outside_target)
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "WRITE_PATH_NOT_ALLOWED")
        self.assertAbsent(outside_target)
        # Deeper falsifier: a path whose PARENT does not exist yet. The gate must
        # fire before the handler's mkdir(parents=True) — no directory may appear.
        deep = self.outside / "deep" / "evil.txt"
        deep_envelope = make_envelope(
            "fals-10-write-outside-deep",
            "filesystem.write",
            payload={"path": str(deep), "content": "nope"},
        )
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(deep_envelope)
        self.assertEqual(ctx.exception.reason, "WRITE_PATH_NOT_ALLOWED")
        self.assertFalse((self.outside / "deep").exists())

    # --- 8. EXECUTABLE_NOT_ALLOWED / EXECUTABLE_NOT_FOUND ----------------------

    def test_executable_not_allowed_nothing_runs(self):
        sentinel = self.read_root / "sentinel.txt"
        envelope = make_envelope(
            "fals-11-exec",
            "process.run",
            payload={
                "argv": ["sh", "-c", "touch " + str(sentinel)],
                "cwd": str(self.read_root),
            },
        )
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "EXECUTABLE_NOT_ALLOWED")
        self.assertAbsent(sentinel)
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "EXECUTABLE_NOT_ALLOWED")
        self.assertAbsent(sentinel)
        # Control: an allowlisted executable runs — the gate is load-bearing.
        control = make_envelope(
            "fals-11-control",
            "process.run",
            payload={
                "argv": ["python3", "-c", "print('control-ran')"],
                "cwd": str(self.read_root),
            },
        )
        result = self.executor.execute(control)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("control-ran", result["stdout"])

    def test_executable_not_found_typed_refusal(self):
        # Precondition: the name is genuinely absent, or which() would resolve
        # and the agent would correctly say EXECUTABLE_NOT_ALLOWED instead.
        if shutil.which(ABSENT_EXECUTABLE) is not None:
            self.skipTest("sentinel executable name unexpectedly present on PATH")
        envelope = make_envelope(
            "fals-12-missing",
            "process.run",
            payload={
                "argv": [ABSENT_EXECUTABLE, "--version"],
                "cwd": str(self.read_root),
            },
        )
        with self.assertRaises(mod.Refused) as ctx:
            self.executor.execute(envelope)
        self.assertEqual(ctx.exception.reason, "EXECUTABLE_NOT_FOUND")
        receipt = self.run_envelope(envelope)
        self.assertRefusedReceipt(receipt, "EXECUTABLE_NOT_FOUND")

    # --- 9. Adversarial: hash-then-mutate vs the court --------------------------

    def test_hash_then_mutate_court_fails_naive_replayer(self):
        # Direction A: relaxing mutation (foreign machine -> this machine).
        scoped = make_envelope(
            "adv-a-original",
            "filesystem.write",
            machine_id=FOREIGN_MACHINE,
            payload={"path": str(self.write_root / "adv-a.txt"), "content": "probe"},
        )
        scoped_seal = sha256_json(scoped)
        relaxed = copy.deepcopy(scoped)
        relaxed["machine"]["id"] = MACHINE_ID  # mutated AFTER hashing
        relaxed["request_id"] = "adv-a-relaxed"  # distinct id: it is a distinct envelope
        self.assertNotEqual(sha256_json(relaxed), scoped_seal)
        # A naive replayer would actuate the FOREIGN-machine envelope...
        self.assertTrue(naive_replayer_would_actuate(scoped))
        # ...but the court refuses it with a typed reason and zero mutation.
        refused = self.run_envelope(scoped)
        self.assertRefusedReceipt(refused, "MACHINE_SCOPE_VIOLATION")
        self.assertAbsent(self.write_root / "adv-a.txt")
        # The post-hash mutation CHANGES the court's detection outcome: the
        # relaxed twin is a different envelope (different seal) and actuates.
        allowed = self.run_envelope(relaxed)
        self.assertEqual(allowed["standing"], "ALIVE")
        self.assertTrue((self.write_root / "adv-a.txt").exists())
        self.assertNotEqual(allowed["request_sha256"], refused["request_sha256"])
        self.assertEqual(allowed["request_sha256"], sha256_json(relaxed))

        # Direction B: expiring mutation (valid -> expired after hashing).
        live = make_envelope(
            "adv-b-original",
            "filesystem.write",
            payload={"path": str(self.write_root / "adv-b.txt"), "content": "probe"},
            expires_at=FAR_FUTURE_AT,
        )
        live_seal = sha256_json(live)
        expired = copy.deepcopy(live)
        expired["expires_at"] = EXPIRED_AT  # mutated AFTER hashing
        self.assertNotEqual(sha256_json(expired), live_seal)
        # Naive replayer (ignores expiry) would actuate the expired envelope...
        self.assertTrue(naive_replayer_would_actuate(expired))
        # ...but the court refuses it, and the pre-recorded seal proves the
        # on-disk envelope is not the one that was sealed.
        receipt = self.run_envelope(expired)
        self.assertRefusedReceipt(receipt, "REQUEST_EXPIRED")
        self.assertAbsent(self.write_root / "adv-b.txt")
        self.assertEqual(receipt["request_sha256"], sha256_json(expired))
        self.assertNotEqual(receipt["request_sha256"], live_seal)

    def test_receipt_digest_is_canonical_semantic_seal(self):
        # The agent hashes the PARSED envelope canonically, not the raw bytes:
        # a differently-formatted on-disk file yields the same canonical digest,
        # and any field mutation yields a different one.
        envelope = make_envelope(
            "adv-c-seal",
            "filesystem.write",
            payload={"path": str(self.write_root / "adv-c.txt"), "content": "seal"},
        )
        expected = sha256_json(envelope)
        receipt = self.run_envelope(envelope)  # run_envelope writes non-canonical JSON
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertEqual(receipt["request_sha256"], expected)
        for mutate in (
            lambda e: e["payload"].update({"content": "tampered"}),
            lambda e: e["machine"].update({"id": FOREIGN_MACHINE}),
            lambda e: e.update({"operation": "filesystem.read"}),
        ):
            variant = copy.deepcopy(envelope)
            mutate(variant)
            self.assertNotEqual(
                sha256_json(variant),
                expected,
                "field mutation must change the canonical digest",
            )

    # --- no real $HOME ever touched ---------------------------------------------

    def test_roots_are_temporary_not_home(self):
        for root in (self.read_root, self.write_root, self.outside):
            self.assertTrue(str(root).startswith(self.tmp.name))
            self.assertNotIn(str(Path.home()), str(root))


if __name__ == "__main__":
    unittest.main()
