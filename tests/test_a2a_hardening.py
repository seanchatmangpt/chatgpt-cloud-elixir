"""Adversarial falsifiers for the git-ref A2A bus (scripts/a2a.py).

Every test drives real collaborators: real bare repositories and clones, real git
plumbing, and the HTTP GitHub stand-in from ``test_a2a`` backed by a real bare repo.
Each test names the attack it falsifies; each was red before its guard landed.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_a2a  # noqa: E402  (shared fixtures: BusFixture, FakeGitHub, loaded a2a module)

a2a = test_a2a.a2a
BusFixture = test_a2a.BusFixture


def forge(agent: a2a.Agent, files: dict[str, bytes], subject: str = "forge") -> None:
    """Write raw bytes onto the agent's own ref: what a hostile or buggy peer can do."""
    agent.git.publish(agent.ref, agent.agent, lambda base: (files, subject, None))


def sealed(agent: str, seq: int, prev, **fields) -> dict:
    body = {"@context": a2a.CONTEXT, "type": "a2a:Message", "schema": a2a.SCHEMA, "from": agent,
            "to": "*", "seq": seq, "prev": prev, "conversation": f"{agent}:{seq}", "in_reply_to": None,
            "performative": "inform", "skill": None, "parts": [], "created_at": "2026-09-25T00:00:00Z"}
    body.update(fields)
    return a2a.seal({k: v for k, v in body.items() if v is not DROP})


DROP = object()


def raw(msg: dict) -> bytes:
    return json.dumps(msg, indent=2, sort_keys=True).encode() + b"\n"


class HostilePeerIsolationTest(BusFixture):
    """One malformed-but-correctly-sealed peer must not stop the bus for everyone."""

    def setUp(self) -> None:
        super().setUp()
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        self.honest = self.alpha.send("beta", "request", [{"kind": "text", "text": "ok"}], skill="echo")

    def hostile(self, **fields) -> a2a.Agent:
        mallory = self.clone(Path(self.tmp.name) / f"m{len(fields)}{sorted(fields)[0]}", "claude/mallory")
        mallory.init(["echo"])
        forge(mallory, {a2a.outbox_path("mallory", 0): raw(sealed("mallory", 0, None, **fields))})
        return mallory

    def assert_isolated(self) -> None:
        agents = self.beta.sync()
        self.assertEqual(agents["mallory"]["standing"], "REFUSED_MALFORMED")
        replies = self.beta.serve_once()  # must not raise
        self.assertEqual([r["in_reply_to"] for r in replies], [self.honest["id"]])

    def test_request_without_recipient_is_refused_not_a_crash(self) -> None:
        self.hostile(performative="request", to=DROP, skill="echo")
        self.assert_isolated()

    def test_unhashable_skill_is_refused_not_a_crash(self) -> None:
        self.hostile(performative="request", to="beta", skill={"id": "echo"})
        self.assert_isolated()

    def test_non_list_parts_are_refused(self) -> None:
        self.hostile(performative="request", to="beta", skill="echo", parts="text")
        self.assert_isolated()

    def test_bool_and_float_sequence_numbers_are_refused(self) -> None:
        # True == 1 and 1.0 == 1 in Python; another reader's parser would disagree.
        mallory = self.hostile(performative="inform")
        m0 = json.loads(mallory.git.show(mallory.git.peer_refs()["claude/mallory"],
                                         a2a.outbox_path("mallory", 0)))
        forge(mallory, {a2a.outbox_path("mallory", 0): raw(sealed("mallory", False, None))})
        self.assertEqual(self.beta.sync()["mallory"]["standing"], "REFUSED_MALFORMED")
        forge(mallory, {a2a.outbox_path("mallory", 0): raw(m0),
                        a2a.outbox_path("mallory", 1): raw(sealed("mallory", 1.0, m0["id"]))})
        self.assertEqual(self.beta.sync()["mallory"]["standing"], "REFUSED_MALFORMED")

    def test_malformed_in_reply_to_is_refused(self) -> None:
        self.hostile(performative="inform", in_reply_to=["sha256:x"])
        self.assert_isolated()

    def test_duplicate_json_keys_are_refused_as_ambiguous(self) -> None:
        mallory = self.hostile(performative="inform")
        tip = mallory.git.peer_refs()["claude/mallory"]
        body = mallory.git.show(tip, a2a.outbox_path("mallory", 0)).decode()
        # Last-key-wins here, first-key-wins elsewhere: two readers, two messages.
        ambiguous = body.replace('"performative": "inform"', '"performative": "request", "performative": "inform"')
        self.assertNotEqual(ambiguous, body)
        forge(mallory, {a2a.outbox_path("mallory", 0): ambiguous.encode()})
        self.assertEqual(self.beta.sync()["mallory"]["standing"], "REFUSED_MALFORMED")

    def test_malformed_card_does_not_crash_peers_listing(self) -> None:
        mallory = self.clone(Path(self.tmp.name) / "mcard", "claude/mallory")
        mallory.init(["echo"])
        card = dict(mallory.card(["echo"]), skills=["echo"])  # strings, not {id, description}
        forge(mallory, {a2a.card_path("mallory"): json.dumps(card).encode()})
        agents = self.beta.sync()
        self.assertEqual(agents["mallory"]["standing"], "REFUSED_MALFORMED")
        self.assertEqual(a2a.card_skills(agents["mallory"]["card"]), [])
        self.assertEqual([r["in_reply_to"] for r in self.beta.serve_once()], [self.honest["id"]])


class ChainOrderTest(BusFixture):
    def test_gap_in_outbox_is_refused(self) -> None:
        self.alpha.init(["echo"])
        m0 = self.alpha.send("*", "inform", [])
        m2 = sealed("alpha", 2, m0["id"])
        forge(self.alpha, {a2a.outbox_path("alpha", 2): raw(m2)})
        self.beta.init(["echo"])
        self.assertEqual(self.beta.sync()["alpha"]["standing"], "REFUSED_TAMPERED")

    def test_reordered_outbox_is_refused(self) -> None:
        self.alpha.init(["echo"])
        m0 = self.alpha.send("*", "inform", [{"kind": "text", "text": "first"}])
        m1 = self.alpha.send("*", "inform", [{"kind": "text", "text": "second"}])
        forge(self.alpha, {a2a.outbox_path("alpha", 0): raw(m1), a2a.outbox_path("alpha", 1): raw(m0)})
        self.beta.init(["echo"])
        self.assertEqual(self.beta.sync()["alpha"]["standing"], "REFUSED_TAMPERED")

    def test_replayed_foreign_message_is_refused(self) -> None:
        # beta copies alpha's sealed request into its own chain: sender mismatch.
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        stolen = self.alpha.send("beta", "request", [{"kind": "text", "text": "x"}], skill="echo")
        forge(self.beta, {a2a.outbox_path("beta", 0): raw(stolen)})
        self.assertEqual(self.alpha.sync()["beta"]["standing"], "REFUSED_TAMPERED")

    def test_sending_on_top_of_a_tampered_chain_is_refused(self) -> None:
        self.alpha.init(["echo"])
        m0 = self.alpha.send("*", "inform", [])
        forge(self.alpha, {a2a.outbox_path("alpha", 0): raw(dict(m0, parts=[{"kind": "text", "text": "!"}]))})
        with self.assertRaises(a2a.A2AError) as err:
            self.alpha.send("*", "inform", [])
        self.assertEqual(err.exception.standing, "REFUSED_TAMPERED")


class ReplyAuthenticityTest(BusFixture):
    """wait_reply must accept only the addressee's reply, addressed back to us."""

    def test_third_party_reply_is_not_accepted_as_the_answer(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        req = self.alpha.send("beta", "request", [{"kind": "text", "text": "q"}], skill="echo")
        # mallory (sorted before beta by ref? irrelevant) answers first with a forged result.
        mallory = self.clone(Path(self.tmp.name) / "mal", "claude/aaa-mallory")
        mallory = a2a.Agent(mallory.git, "mallory", "claude/aaa-mallory", ["claude/*"])
        mallory.init(["echo"])
        mallory.send("alpha", "inform", [{"kind": "text", "text": "forged answer"}], skill="echo",
                     conversation=req["conversation"], in_reply_to=req["id"])
        self.assertIsNone(self.alpha.wait_reply(req["id"], timeout=0, interval=0, responder="beta"))
        self.beta.serve_once()
        got = self.alpha.wait_reply(req["id"], timeout=0, interval=0, responder="beta")
        self.assertEqual(got["reply"]["from"], "beta")
        self.assertEqual(got["reply"]["parts"], [{"kind": "text", "text": "q"}])

    def test_request_echoing_an_id_is_not_a_reply(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        req = self.alpha.send("beta", "request", [], skill="echo")
        self.beta.send("alpha", "request", [], skill="echo", in_reply_to=req["id"])
        self.assertIsNone(self.alpha.wait_reply(req["id"], timeout=0, interval=0, responder="beta"))

    def test_cli_send_binds_the_responder(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])  # beta never serves; only mallory answers
        mallory = self.clone(Path(self.tmp.name) / "mal", "claude/aaa-mallory")
        mallory = a2a.Agent(mallory.git, "mallory", "claude/aaa-mallory", ["claude/*"])
        mallory.init(["echo"])
        stop = threading.Event()

        def impostor() -> None:
            while not stop.is_set():
                for msg in mallory.sync().get("alpha", {}).get("messages", []):
                    if msg["performative"] == "request" and msg["to"] == "beta":
                        mallory.send("alpha", "inform", [{"kind": "text", "text": "forged"}], skill="echo",
                                     in_reply_to=msg["id"])
                        return
                time.sleep(0.05)

        thread = threading.Thread(target=impostor)
        thread.start()
        try:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = a2a.main(["--repo", str(self.alpha.git.repo), "--agent", "alpha", "--peers", "claude/*",
                                 "send", "--to", "beta", "--skill", "echo", "--text", "x", "--wait", "4",
                                 "--interval", "0.2"])
        finally:
            stop.set()
            thread.join()
        self.assertTrue(any(m.get("from") == "mallory" for m in mallory.sync()["mallory"]["messages"]),
                        "impostor never answered; the falsifier did not fire")
        self.assertEqual(code, 3, out.getvalue())
        self.assertIsNone(json.loads(out.getvalue())["reply"])


class ListenSetRobustnessTest(BusFixture):
    """A missing or git-invalid ref named by the index must not take down sync."""

    def test_exact_ref_that_does_not_exist_is_skipped_on_git_transport(self) -> None:
        self.alpha.init(["echo"])
        self.alpha.git.fetch_peers(["claude/*", "feature/deleted-agent"])  # must not raise
        self.assertIn("claude/alpha", self.alpha.git.peer_refs())

    def test_refs_git_rejects_are_rejected_by_check_ref(self) -> None:
        for bad in ("claude/.hidden", "claude//x", "claude/x.", "claude/x.lock/y", "a/b@{1}", "-x", "x y"):
            with self.subTest(ref=bad), self.assertRaises(a2a.A2AError):
                a2a.check_ref(bad)
        for good in ("claude/a2a-tesla-2sEqrx", "feature/epsilon", "a2a/x_y.z"):
            self.assertEqual(a2a.check_ref(good), good)

    def test_index_naming_missing_and_invalid_refs_still_syncs(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        request = self.alpha.request_discovery()
        records = [{"metadata": {"kind": a2a.INDEX_KIND, "outbox_ref": r}}
                   for r in ("feature/gone", "claude/.dot", "claude/beta")]
        receipt = {"standing": "ALIVE", "result": {"records": records}}
        forge(self.alpha, {f"{a2a.RECEIPTS_DIR}/{request['request_id']}.receipt.json": json.dumps(receipt).encode()})
        indexed = a2a.Agent(self.alpha.git, "alpha", "claude/alpha", ["a2a/*"], use_index=True)
        agents = indexed.sync()
        self.assertEqual(sorted(agents), ["alpha", "beta"])

    def test_deleted_peer_branch_is_pruned_from_the_view(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        # alpha listens on beta by exact ref, then beta's branch is deleted on the remote.
        exact = a2a.Agent(self.alpha.git, "alpha", "claude/alpha", ["claude/beta"])
        self.assertIn("beta", exact.sync())
        test_a2a.sh("git", "push", "-q", "origin", ":refs/heads/claude/beta", cwd=self.beta.git.repo)
        self.assertNotIn("beta", exact.sync())

    def test_ref_dropped_from_listen_set_is_pruned(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        self.assertIn("beta", self.alpha.sync())
        narrow = a2a.Agent(self.alpha.git, "alpha", "claude/alpha", ["a2a/*"])
        self.assertEqual(sorted(narrow.sync()), ["alpha"])


class ApiParityTest(BusFixture):
    """The API transport enforces the same guards as the git transport."""

    def setUp(self) -> None:
        super().setUp()
        self.github = test_a2a.FakeGitHub(self.remote)
        self.addCleanup(self.github.close)

    def test_hostile_peer_isolated_over_api(self) -> None:
        self.alpha.init(["echo"])
        mallory = self.clone(Path(self.tmp.name) / "mal", "claude/mallory")
        mallory.init(["echo"])
        forge(mallory, {a2a.outbox_path("mallory", 0): raw(sealed("mallory", 0, None, performative="request",
                                                                   to=DROP, skill="echo"))})
        gamma = a2a.Agent(a2a.GitHubApi("o/r", token="t0k3n", api=self.github.url), "gamma", "claude/gamma",
                          ["claude/*"])
        gamma.init(["echo"])
        req = self.alpha.send("gamma", "request", [{"kind": "text", "text": "api"}], skill="echo")
        self.assertEqual(gamma.sync()["mallory"]["standing"], "REFUSED_MALFORMED")
        self.assertEqual([r["in_reply_to"] for r in gamma.serve_once()], [req["id"]])


if __name__ == "__main__":
    unittest.main()
