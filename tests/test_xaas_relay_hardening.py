"""Adversarial court for scripts/xaas-relay.py (PR #44 harden round).

Real collaborators only: the relay module is loaded from the repository, state
lives in a real file, and "zcode" is a real executable script whose stdout and
exit code are chosen per case (a genuine gall-work protocol peer, not a mock of
the relay). Every case asserts on returned rows, the spawn counter file, and the
persisted state file.

Defects found and guarded here (all passed silently before this round):
- REPLAY_IDENTITY_MISMATCH: a reused command_id carrying a different payload
  (other base_sha / graph digest) was answered KNOWN_REPLAY ALIVE with the
  cached result of a different subject.
- GALL_RESULT_SUBJECT_MISMATCH: a gall.work-result/1 for another epoch/task/base
  was receipted and persisted as this command's consequence.
- GALL_RESULT_EXIT_CONTRADICTION: nonzero gall-work exit with standing ALIVE was
  reported as ALIVE.
"""
from __future__ import annotations

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
SPEC = importlib.util.spec_from_file_location("xaas_relay_harden", ROOT / "scripts" / "xaas-relay.py")
relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relay)

EPOCH = "11111111-1111-4111-8111-111111111111"


class RelayHarness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.worktree = self.root / "worktree"
        self.worktree.mkdir()
        self.state = self.root / "state.json"
        self.counter = self.root / "count.txt"
        self.zcode = self.root / "zcode"
        self.peer()

    def peer(self, *, exit_code=0, standing="ALIVE", overrides=None, raw=None):
        """Install a real gall-work peer executable with a chosen reply."""
        overrides = overrides or {}
        body = raw if raw is not None else (
            "doc={'schema':'gall.work-result/1','standing':%r,'epoch_id':os.environ['XAAS_EPOCH_ID'],"
            "'outcome':'alive','final_head':'c'*40,'runtime_exit_code':0,"
            "'work_order_iri':os.environ['XAAS_WORK_ORDER_IRI'],'base_sha':os.environ['XAAS_BASE_SHA']}\n"
            "doc.update(%r)\nprint(json.dumps(doc))\n" % (standing, overrides)
        )
        self.zcode.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "p=pathlib.Path(os.environ['COUNTER'])\n"
            "p.write_text(str(int(p.read_text())+1 if p.exists() else 1))\n"
            + body
            + "sys.exit(%d)\n" % exit_code
        )
        self.zcode.chmod(self.zcode.stat().st_mode | stat.S_IXUSR)

    def spawns(self):
        return int(self.counter.read_text()) if self.counter.exists() else 0

    def descriptor(self, **overrides):
        value = {
            "schema": "gall.work-lease/1",
            "work_order_iri": "urn:work:1",
            "checkpoint_iri": "urn:checkpoint:1",
            "graph_digest": "sha256:" + "b" * 64,
            "repository_identity": "owner/repo",
            "base_sha": "a" * 40,
            "epoch_id": EPOCH,
            "worker_id": "worker-1",
            "worktree": str(self.worktree),
        }
        value.update(overrides)
        return value

    def envelope(self, descriptor=None, **overrides):
        d = descriptor or self.descriptor()
        value = {
            "schema": "xaas.remote-relay-envelope/1",
            "command_id": "cmd-1",
            "epoch_id": d["epoch_id"],
            "task_id": d["work_order_iri"],
            "sequence": 1,
            "intent_digest": d["graph_digest"],
            "exact_subject": f"{d['repository_identity']}@{d['base_sha']}",
            "verb": "actuate",
            "expires_at": 10_000,
            "execution_manifest_digest": "manifest-1",
            "authority_ref": "grant-1",
            "channel": "control",
            "payload": d,
        }
        value.update(overrides)
        return value

    def deliver(self, envelope, **kwargs):
        env = dict(os.environ)
        env["COUNTER"] = str(self.counter)
        return relay.run_envelope(
            envelope,
            state_path=self.state,
            manifest_digest=kwargs.pop("manifest_digest", "manifest-1"),
            zcode=str(self.zcode),
            allow_do=kwargs.pop("allow_do", True),
            env=env,
            now_ms=kwargs.pop("now_ms", 5),
            **kwargs,
        )

    def state_doc(self):
        return json.loads(self.state.read_text()) if self.state.exists() else None


class ReplayIdentityTests(RelayHarness):
    def test_reused_command_id_with_other_subject_is_refused_not_replayed(self):
        first = self.deliver(self.envelope())
        self.assertEqual(first["reason"], "EXECUTED_RECEIPTED")
        forged = self.descriptor(base_sha="d" * 40, graph_digest="sha256:" + "e" * 64)
        row = self.deliver(self.envelope(forged))
        self.assertEqual(row["standing"], "REFUSED")
        self.assertEqual(row["reason"], "REPLAY_IDENTITY_MISMATCH")
        self.assertFalse(row["executed"])
        self.assertNotIn("result", row)
        self.assertEqual(self.spawns(), 1)

    def test_identical_redelivery_is_known_replay_with_same_digest(self):
        first = self.deliver(self.envelope())
        for _ in range(5):
            row = self.deliver(self.envelope())
            self.assertEqual(row["reason"], "KNOWN_REPLAY")
            self.assertEqual(row["result_digest"], first["result_digest"])
        self.assertEqual(self.spawns(), 1)

    def test_state_row_binds_identity_digest(self):
        self.deliver(self.envelope())
        row = self.state_doc()["results"]["cmd-1"]
        self.assertEqual(row["identity_digest"], relay.identity_digest(self.descriptor()))

    def test_legacy_state_row_without_identity_still_replays(self):
        self.deliver(self.envelope())
        doc = self.state_doc()
        del doc["results"]["cmd-1"]["identity_digest"]
        self.state.write_text(json.dumps(doc))
        row = self.deliver(self.envelope())
        self.assertEqual(row["reason"], "KNOWN_REPLAY")
        self.assertEqual(self.spawns(), 1)

    def test_descriptor_mode_worktree_change_is_a_new_identity(self):
        env = dict(os.environ, COUNTER=str(self.counter))
        kwargs = dict(state_path=self.state, manifest_digest="m", zcode=str(self.zcode), allow_do=True, env=env)
        relay.run_descriptor(self.descriptor(), **kwargs)
        other = self.root / "other"
        other.mkdir()
        row = relay.run_descriptor(self.descriptor(worktree=str(other)), **kwargs)
        self.assertEqual(row["reason"], "EXECUTED_RECEIPTED")
        self.assertEqual(self.spawns(), 2)


class ResultBindingTests(RelayHarness):
    def assert_not_receipted(self, row, reason):
        self.assertEqual(row["standing"], "BUILD_BROKEN")
        self.assertEqual(row["reason"], reason)
        self.assertTrue(row["executed"])
        self.assertIsNone(self.state_doc())

    def test_result_for_other_epoch_is_not_receipted(self):
        self.peer(overrides={"epoch_id": "22222222-2222-4222-8222-222222222222"})
        row = self.deliver(self.envelope())
        self.assert_not_receipted(row, "GALL_RESULT_SUBJECT_MISMATCH")
        self.assertEqual(row["detail"], ["epoch_id"])

    def test_result_for_other_task_and_base_is_not_receipted(self):
        self.peer(overrides={"work_order_iri": "urn:work:9", "base_sha": "f" * 40})
        row = self.deliver(self.envelope())
        self.assert_not_receipted(row, "GALL_RESULT_SUBJECT_MISMATCH")
        self.assertEqual(row["detail"], ["work_order_iri", "base_sha"])

    def test_result_without_identity_fields_is_accepted(self):
        raw = "print(json.dumps({'schema':'gall.work-result/1','standing':'ALIVE','outcome':'alive'}))\n"
        self.peer(raw=raw)
        row = self.deliver(self.envelope())
        self.assertEqual(row["reason"], "EXECUTED_RECEIPTED")

    def test_nonzero_exit_claiming_alive_is_build_broken(self):
        self.peer(exit_code=3, standing="ALIVE")
        row = self.deliver(self.envelope())
        self.assert_not_receipted(row, "GALL_RESULT_EXIT_CONTRADICTION")
        self.assertEqual(row["exit_code"], 3)

    def test_nonzero_exit_lowercase_alive_is_build_broken(self):
        # Adversarial input A2 (court 3647b357): a non-canonical live token must
        # not pass through as the standing of a failed gall-work run.
        for token in ("alive", " Alive ", "partial_alive"):
            with self.subTest(token=token):
                self.peer(exit_code=3, standing=token)
                row = self.deliver(self.envelope())
                self.assert_not_receipted(row, "GALL_RESULT_EXIT_CONTRADICTION")
                self.assertEqual(row["exit_code"], 3)

    def test_nonzero_exit_partial_alive_is_build_broken(self):
        self.peer(exit_code=1, standing="PARTIAL_ALIVE")
        self.assert_not_receipted(self.deliver(self.envelope()), "GALL_RESULT_EXIT_CONTRADICTION")

    def test_nonzero_exit_typed_refusal_keeps_its_standing_and_retries(self):
        self.peer(exit_code=1, standing="REFUSED_CLAIM", overrides={"code": "no_ready_work"})
        row = self.deliver(self.envelope())
        self.assertEqual(row["standing"], "REFUSED_CLAIM")
        self.assertEqual(row["reason"], "no_ready_work")
        self.assertIsNone(self.state_doc())
        self.peer()
        self.assertEqual(self.deliver(self.envelope())["reason"], "EXECUTED_RECEIPTED")
        self.assertEqual(self.spawns(), 2)

    def test_garbage_stdout_is_protocol_failure(self):
        self.peer(raw="print('not json'); print(json.dumps({'schema':'other/1'}))\n")
        row = self.deliver(self.envelope())
        self.assert_not_receipted(row, "GALL_RESULT_PROTOCOL")


class EnvelopeBoundaryTests(RelayHarness):
    def refused(self, envelope, reason, **kwargs):
        row = self.deliver(envelope, **kwargs)
        self.assertEqual((row["standing"], row["reason"]), ("REFUSED", reason), row)
        self.assertFalse(row["executed"])
        self.assertEqual(self.spawns(), 0)

    def test_malformed_shapes(self):
        self.refused([], "ENVELOPE_SHAPE")
        self.refused(self.envelope(schema="xaas.remote-relay-envelope/2"), "ENVELOPE_SCHEMA")
        self.refused(self.envelope(command_id="  "), "ENVELOPE_FIELD:command_id")
        self.refused(self.envelope(verb=7), "ENVELOPE_FIELD:verb")
        self.refused(self.envelope(channel="side"), "INVALID_CHANNEL")

    def test_sequence_types(self):
        for bad in (0, -1, True, "1", 1.0, None):
            self.refused(self.envelope(sequence=bad), "INVALID_SEQUENCE")

    def test_expiry_boundary(self):
        self.refused(self.envelope(expires_at=4), "COMMAND_EXPIRED", now_ms=5)
        self.refused(self.envelope(expires_at=True), "COMMAND_EXPIRED")
        self.refused(self.envelope(expires_at="10000"), "COMMAND_EXPIRED")
        row = self.deliver(self.envelope(expires_at=5), now_ms=5)
        self.assertEqual(row["reason"], "EXECUTED_RECEIPTED")

    def test_descriptor_payload_refusals(self):
        self.refused(self.envelope(payload=None), "DESCRIPTOR_SCHEMA")
        for field, value, reason in (
            ("graph_digest", "sha256:XYZ", "DESCRIPTOR_GRAPH_DIGEST"),
            ("repository_identity", "no-slash", "DESCRIPTOR_REPOSITORY"),
            ("base_sha", "A" * 40, "DESCRIPTOR_BASE_SHA"),
            ("epoch_id", "not-a-uuid", "DESCRIPTOR_EPOCH_ID"),
            ("worker_id", "bad worker", "DESCRIPTOR_WORKER_ID"),
            ("worktree", "relative/path", "DESCRIPTOR_WORKTREE"),
            ("work_order_iri", "nocolon", "DESCRIPTOR_IRI"),
        ):
            d = self.descriptor(**{field: value})
            self.refused(self.envelope(d), reason)

    def test_observe_channel_non_actuate_needs_no_authority_but_still_needs_do_ack(self):
        row = self.deliver(self.envelope(verb="observe", channel="observe", authority_ref=None), allow_do=False)
        self.assertEqual(row["reason"], "EXPLICIT_DO_ACK_REQUIRED")
        self.assertEqual(self.spawns(), 0)

    def test_manifest_drift_against_persisted_state(self):
        self.deliver(self.envelope())
        row = self.deliver(self.envelope(execution_manifest_digest="m-2"), manifest_digest="m-2")
        self.assertEqual(row["reason"], "EXECUTION_MANIFEST_DRIFT")
        self.assertEqual(self.spawns(), 1)

    def test_corrupt_state_file_refuses_without_spawn(self):
        self.state.write_text("{not json")
        row = self.deliver(self.envelope())
        self.assertEqual(row["standing"], "REFUSED")
        self.assertEqual(self.spawns(), 0)
        self.state.write_text(json.dumps({"schema": "other"}))
        self.assertEqual(self.deliver(self.envelope())["reason"], "STATE_SCHEMA")


class OrderingTests(RelayHarness):
    def envelope_n(self, n):
        return self.envelope(command_id=f"cmd-{n}", sequence=n)

    def test_reordered_delivery_gap_then_in_order(self):
        self.assertEqual(self.deliver(self.envelope_n(2))["reason"], "SEQUENCE_GAP")
        self.assertEqual(self.deliver(self.envelope_n(1))["reason"], "EXECUTED_RECEIPTED")
        self.assertEqual(self.deliver(self.envelope_n(2))["reason"], "EXECUTED_RECEIPTED")
        self.assertEqual(self.state_doc()["last_acknowledged_sequence"], 2)
        self.assertEqual(self.spawns(), 2)

    def test_stale_sequence_with_fresh_id_never_spawns(self):
        self.deliver(self.envelope_n(1))
        stale = self.envelope(command_id="cmd-new", sequence=1)
        row = self.deliver(stale)
        self.assertEqual(row["reason"], "KNOWN_REPLAY")
        self.assertFalse(row["executed"])
        self.assertNotIn("result", row)
        self.assertEqual(self.spawns(), 1)

    def test_dedup_bound_evicts_results_but_sequence_still_blocks_reexecution(self):
        for n in range(1, 6):
            self.assertEqual(self.deliver(self.envelope_n(n), dedup_limit=2)["reason"], "EXECUTED_RECEIPTED")
        doc = self.state_doc()
        self.assertEqual(sorted(doc["results"]), ["cmd-4", "cmd-5"])
        self.assertEqual(doc["seen_command_ids"], ["cmd-5", "cmd-4"])
        row = self.deliver(self.envelope_n(1), dedup_limit=2)
        self.assertEqual(row["reason"], "KNOWN_REPLAY")
        self.assertEqual(self.spawns(), 5)


class CliExitCodeTests(RelayHarness):
    def cli(self, envelope, *extra):
        path = self.root / "env.json"
        path.write_text(json.dumps(envelope))
        env = dict(os.environ, COUNTER=str(self.counter))
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "xaas-relay.py"), "--envelope", str(path),
             "--state", str(self.state), "--manifest-digest", "manifest-1", "--zcode", str(self.zcode), *extra],
            capture_output=True, text=True, env=env, timeout=60, check=False,
        )

    def test_cli_replay_mismatch_exits_77(self):
        # expires_at far in the future: the CLI uses wall-clock time.
        far = 2 ** 62
        self.assertEqual(self.cli(self.envelope(expires_at=far), "--allow-do").returncode, 0)
        forged = self.envelope(self.descriptor(base_sha="d" * 40, graph_digest="sha256:" + "e" * 64), expires_at=far)
        done = self.cli(forged, "--allow-do")
        self.assertEqual(done.returncode, 77, done.stdout)
        self.assertEqual(json.loads(done.stdout)["reason"], "REPLAY_IDENTITY_MISMATCH")

    def test_cli_exit_contradiction_exits_69(self):
        self.peer(exit_code=2, standing="ALIVE")
        done = self.cli(self.envelope(expires_at=2 ** 62), "--allow-do")
        self.assertEqual(done.returncode, 69, done.stdout)
        self.assertEqual(json.loads(done.stdout)["reason"], "GALL_RESULT_EXIT_CONTRADICTION")


if __name__ == "__main__":
    unittest.main()
