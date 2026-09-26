"""Two isolated clones of one bare remote stand in for two ephemeral instances."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("a2a", Path(__file__).resolve().parents[1] / "scripts" / "a2a.py")
a2a = importlib.util.module_from_spec(SPEC)
sys.modules["a2a"] = a2a
SPEC.loader.exec_module(a2a)


def sh(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class A2ABusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.remote = root / "remote.git"
        sh("git", "init", "--bare", "-q", "-b", "main", str(self.remote), cwd=root)
        seed = root / "seed"
        sh("git", "init", "-q", "-b", "main", str(seed), cwd=root)
        (seed / "README").write_text("seed\n")
        sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "add", ".", cwd=seed)
        sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed", cwd=seed)
        sh("git", "push", "-q", str(self.remote), "main:main", cwd=seed)
        self.alpha = self.clone(root / "alpha", "claude/alpha")
        self.beta = self.clone(root / "beta", "claude/beta")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def clone(self, path: Path, ref: str) -> a2a.Agent:
        sh("git", "clone", "-q", str(self.remote), str(path), cwd=path.parent)
        sh("git", "checkout", "-qb", ref, cwd=path)
        return a2a.Agent(a2a.Git(path, "origin"), ref.split("/")[1], ref, ["claude/*"])

    def test_request_reply_across_instances_is_idempotent(self) -> None:
        self.alpha.init(["ping", "echo"])
        self.beta.init(["echo", "digest"])
        req = self.alpha.send("beta", "request", [{"kind": "text", "text": "hi"}], skill="echo")
        bad = self.alpha.send("beta", "request", [], skill="ping")  # beta does not offer ping
        replies = self.beta.serve_once()
        self.assertEqual([r["in_reply_to"] for r in replies], [req["id"], bad["id"]])
        self.assertEqual(replies[0]["parts"], [{"kind": "text", "text": "hi"}])
        self.assertEqual(replies[1]["performative"], "refuse")
        self.assertEqual(self.beta.serve_once(), [])  # ledger-derived idempotence
        got = self.alpha.wait_reply(req["id"], timeout=0, interval=0)
        self.assertEqual(got["reply"]["from"], "beta")
        self.assertEqual(got["responder_ref"], "claude/beta")

    def test_hash_chain_links_messages(self) -> None:
        self.alpha.init(["echo"])
        m0 = self.alpha.send("*", "inform", [])
        m1 = self.alpha.send("*", "inform", [])
        self.assertEqual((m0["seq"], m0["prev"]), (0, None))
        self.assertEqual((m1["seq"], m1["prev"]), (1, m0["id"]))

    def test_tampered_chain_is_refused(self) -> None:
        self.alpha.init(["echo"])
        msg = self.alpha.send("beta", "request", [{"kind": "text", "text": "x"}], skill="echo")
        forged = dict(msg, parts=[{"kind": "text", "text": "forged"}])
        git = self.alpha.git
        git.publish("claude/alpha", "alpha", lambda base: (
            {a2a.outbox_path("alpha", 0): json.dumps(forged).encode()}, "forge", None))
        self.beta.init(["echo"])
        view = self.beta.sync()["alpha"]
        self.assertEqual(view["standing"], "REFUSED_TAMPERED")
        self.assertEqual(self.beta.serve_once(), [])

    def test_copied_agent_on_foreign_ref_is_not_authoritative(self) -> None:
        self.alpha.init(["echo"])
        card = json.dumps({**self.alpha.card(["echo"]), "agent": "alpha"}).encode()
        # beta's branch carries a copy of alpha's card claiming alpha's ref: ignored there.
        self.beta.git.publish("claude/beta", "beta", lambda base: ({a2a.card_path("alpha"): card}, "copy", None))
        agents = self.beta.sync()
        self.assertEqual(agents["alpha"]["ref"], "claude/alpha")

    def test_concurrent_writer_race_rebuilds_on_new_tip(self) -> None:
        self.alpha.init(["echo"])
        # A second container for the same agent pushes first; alpha must not clobber it.
        other = self.clone(Path(self.tmp.name) / "alpha2", "claude/alpha-tmp")
        other = a2a.Agent(other.git, "alpha", "claude/alpha", ["claude/*"])
        m0 = other.send("*", "inform", [])
        m1 = self.alpha.send("*", "inform", [])
        self.assertEqual(m1["seq"], 1)
        self.assertEqual(m1["prev"], m0["id"])

    def test_malformed_identifiers_are_refused(self) -> None:
        with self.assertRaises(a2a.A2AError):
            a2a.check_agent_id("../x")
        with self.assertRaises(a2a.A2AError):
            a2a.check_ref("claude/../main")


if __name__ == "__main__":
    unittest.main()
