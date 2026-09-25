import importlib.util
import json
import os
import pathlib
import stat
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

    def run(self, **kwargs):
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
        row = self.run()
        self.assertEqual(row["standing"], "REFUSED_AUTHORITY")
        self.assertFalse(row["executed"])
        self.assertFalse(self.counter.exists())

    def test_success_is_durable_and_duplicate_replays_without_process(self):
        first = self.run(allow_do=True)
        self.assertEqual(first["standing"], "ALIVE")
        self.assertTrue(first["executed"])
        self.assertEqual(self.counter.read_text(), "1")

        second = self.run(allow_do=True)
        self.assertEqual(second["reason"], "KNOWN_REPLAY")
        self.assertFalse(second["executed"])
        self.assertEqual(second["result_digest"], first["result_digest"])
        self.assertEqual(self.counter.read_text(), "1")

    def test_manifest_drift_refuses_before_process(self):
        self.run(allow_do=True)
        drift = self.run(allow_do=True, manifest_digest="manifest-2")
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


if __name__ == "__main__":
    unittest.main()
