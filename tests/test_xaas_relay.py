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
            "print(json.dumps({'schema':'gall.work-result/1','standing':'ALIVE','epoch_id':'11111111-1111-4111-8111-111111111111','outcome':'alive','final_head':'a'*40,'runtime_exit_code':0}))\n"
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
