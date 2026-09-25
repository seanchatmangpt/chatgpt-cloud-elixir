"""Two isolated clones of one bare remote stand in for two ephemeral instances."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

SPEC = importlib.util.spec_from_file_location("a2a", Path(__file__).resolve().parents[1] / "scripts" / "a2a.py")
a2a = importlib.util.module_from_spec(SPEC)
sys.modules["a2a"] = a2a
SPEC.loader.exec_module(a2a)
a2a.PUSH_BACKOFF = 0.0

PROXY_SPEC = importlib.util.spec_from_file_location(
    "project_memory_proxy", Path(__file__).resolve().parents[1] / "scripts" / "project_memory_proxy.py")
proxy = importlib.util.module_from_spec(PROXY_SPEC)
sys.modules["project_memory_proxy"] = proxy
PROXY_SPEC.loader.exec_module(proxy)


def sh(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class BusFixture(unittest.TestCase):
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


class A2ABusTest(BusFixture):
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


class FakeGitHub:
    """The slice of the GitHub REST git data API that ``GitHubApi`` uses, served over
    HTTP and backed by a real bare repository, so API and git peers share objects."""

    def __init__(self, bare: Path, token: str = "t0k3n"):
        self.bare = bare
        self.token = token
        self.before_patch = None  # hook: lets a test lose a ref-update race
        self.calls: list[str] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # quiet
                pass

            def _send(self, code, body=None):
                raw = json.dumps(body).encode() if body is not None else b""
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _dispatch(self, method):
                url = urlparse(self.path)
                prefix = "/repos/o/r/"
                path = unquote(url.path)
                fake.calls.append(f"{method} {path}")
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                if method != "GET" and self.headers.get("Authorization") != f"Bearer {fake.token}":
                    return self._send(401, {"message": "Bad credentials"})
                if path == "/repos/o/r":
                    return self._send(200, {"default_branch": "main"})
                if not path.startswith(prefix):
                    return self._send(404, {"message": "Not Found"})
                code, out = fake.route(method, path[len(prefix):], dict(
                    kv.split("=", 1) for kv in url.query.split("&") if "=" in kv), body)
                return self._send(code, out)

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

            def do_PATCH(self):
                self._dispatch("PATCH")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def git(self, *args, stdin=None, env=None, check=True):
        proc = subprocess.run(["git", "-C", str(self.bare), *args], input=stdin, capture_output=True,
                              env={**os.environ, **(env or {})})
        if check and proc.returncode:
            raise RuntimeError(proc.stderr.decode())
        return proc

    def head(self, ref):
        proc = self.git("rev-parse", "--verify", "-q", f"refs/heads/{ref}", check=False)
        return proc.stdout.decode().strip() or None

    def route(self, method, path, query, body):
        if method == "GET" and path.startswith("git/ref/heads/"):
            sha = self.head(path[len("git/ref/heads/"):])
            return (200, {"ref": path[4:], "object": {"sha": sha}}) if sha else (404, {"message": "Not Found"})
        if method == "GET" and (path == "git/matching-refs/heads" or path.startswith("git/matching-refs/heads/")):
            prefix = path[len("git/matching-refs/heads/"):]
            rows = []
            for line in self.git("for-each-ref", "--format=%(objectname) %(refname)", "refs/heads/") \
                    .stdout.decode().splitlines():
                sha, name = line.split(" ", 1)
                if name[len("refs/heads/"):].startswith(prefix):
                    rows.append({"ref": name, "object": {"sha": sha}})
            per, page = int(query.get("per_page", 30)), int(query.get("page", 1))
            return 200, rows[(page - 1) * per:page * per]
        if method == "GET" and path.startswith("git/commits/"):
            tree = self.git("rev-parse", path[len("git/commits/"):] + "^{tree}").stdout.decode().strip()
            return 200, {"tree": {"sha": tree}}
        if method == "GET" and path.startswith("git/trees/"):
            entries = []
            for line in self.git("ls-tree", "-r", path[len("git/trees/"):]).stdout.decode().splitlines():
                meta, name = line.split("\t", 1)
                mode, kind, sha = meta.split()
                entries.append({"path": name, "mode": mode, "type": kind, "sha": sha})
            return 200, {"tree": entries, "truncated": False}
        if method == "GET" and path.startswith("git/blobs/"):
            raw = self.git("cat-file", "blob", path[len("git/blobs/"):]).stdout
            return 200, {"content": base64.b64encode(raw).decode(), "encoding": "base64"}
        if method == "POST" and path == "git/trees":
            with tempfile.TemporaryDirectory() as tmp:
                env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
                self.git("read-tree", body["base_tree"], env=env)
                for entry in body["tree"]:
                    blob = self.git("hash-object", "-w", "--stdin", stdin=entry["content"].encode()) \
                        .stdout.decode().strip()
                    self.git("update-index", "--add", "--cacheinfo", f"{entry['mode']},{blob},{entry['path']}",
                             env=env)
                return 201, {"sha": self.git("write-tree", env=env).stdout.decode().strip()}
        if method == "POST" and path == "git/commits":
            who = body["author"]
            env = {"GIT_AUTHOR_NAME": who["name"], "GIT_AUTHOR_EMAIL": who["email"],
                   "GIT_COMMITTER_NAME": who["name"], "GIT_COMMITTER_EMAIL": who["email"]}
            args = ["commit-tree", body["tree"], "-m", body["message"]]
            for parent in body["parents"]:
                args += ["-p", parent]
            return 201, {"sha": self.git(*args, env=env).stdout.decode().strip()}
        if method == "POST" and path == "git/refs":
            ok = self.git("update-ref", body["ref"], body["sha"], "0" * 40, check=False).returncode == 0
            return (201, {"ref": body["ref"]}) if ok else (422, {"message": "Reference already exists"})
        if method == "PATCH" and path.startswith("git/refs/heads/"):
            ref = path[len("git/refs/heads/"):]
            if self.before_patch:
                hook, self.before_patch = self.before_patch, None
                hook()
            old = self.head(ref)
            ff = self.git("merge-base", "--is-ancestor", old, body["sha"], check=False).returncode == 0
            if not ff and not body.get("force"):
                return 422, {"message": "Update is not a fast forward"}
            self.git("update-ref", f"refs/heads/{ref}", body["sha"], old)
            return 200, {"object": {"sha": body["sha"]}}
        return 404, {"message": f"unrouted {method} {path}"}

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class ApiTransportTest(BusFixture):
    """A peer with HTTPS but no git (a ChatGPT container) interoperates with git peers."""

    def setUp(self) -> None:
        super().setUp()
        self.github = FakeGitHub(self.remote)
        self.addCleanup(self.github.close)
        self.gamma = self.api_agent("gamma", "claude/gamma")

    def api_agent(self, agent, ref, token="t0k3n", peers=("claude/*",)):
        return a2a.Agent(a2a.GitHubApi("o/r", token=token, api=self.github.url), agent, ref, list(peers))

    def test_api_peer_and_git_peer_exchange_both_ways(self) -> None:
        self.alpha.init(["echo"])
        card = self.gamma.init(["ping", "digest"])
        self.assertEqual(card["repository"], "https://github.com/o/r")
        req = self.alpha.send("gamma", "request", [{"kind": "text", "text": "A = mu(O)"}], skill="digest")
        [reply] = self.gamma.serve_once()
        self.assertEqual(reply["in_reply_to"], req["id"])
        got = self.alpha.wait_reply(req["id"], timeout=0, interval=0)
        self.assertEqual(got["responder_ref"], "claude/gamma")
        self.assertEqual(got["reply"]["parts"][0]["data"]["sha256"],
                         "ca1ebebd535f2c389ffa4c3caf52f91d9d8070a145d3176242ef599b624315bc")
        back = self.gamma.send("alpha", "request", [{"kind": "text", "text": "hi"}], skill="echo")
        self.assertEqual([r["in_reply_to"] for r in self.alpha.serve_once()], [back["id"]])
        self.assertEqual(self.gamma.wait_reply(back["id"], timeout=0, interval=0)["reply"]["parts"],
                         [{"kind": "text", "text": "hi"}])
        # both transports read the same verified ledger
        self.assertEqual(self.gamma.sync()["alpha"]["commit"], self.alpha.sync()["alpha"]["commit"])

    def test_api_new_ref_starts_from_default_branch(self) -> None:
        self.gamma.init(["ping"])
        main = self.github.head("main")
        tip = self.github.head("claude/gamma")
        self.assertEqual(self.github.git("rev-parse", f"{tip}^").stdout.decode().strip(), main)

    def test_api_lost_race_rebuilds_on_new_tip(self) -> None:
        self.gamma.init(["ping"])
        rival = self.api_agent("gamma", "claude/gamma")
        self.github.before_patch = lambda: rival.send("*", "inform", [{"kind": "text", "text": "rival"}])
        mine = self.gamma.send("*", "inform", [{"kind": "text", "text": "mine"}])
        self.assertEqual(sum(c.startswith("PATCH") for c in self.github.calls), 3)  # lost once, retried
        chain = self.alpha.sync()["gamma"]["messages"]
        self.assertEqual([m["seq"] for m in chain], [0, 1])
        self.assertEqual(chain[1]["id"], mine["id"])
        self.assertEqual(mine["prev"], chain[0]["id"])

    def test_api_write_without_authority_is_blocked_not_faked(self) -> None:
        anon = self.api_agent("delta", "claude/delta", token=None)
        with self.assertRaises(a2a.A2AError) as err:
            anon.init(["ping"])
        self.assertEqual(err.exception.standing, "BLOCKED")
        self.assertIsNone(self.github.head("claude/delta"))
        # reads still work unauthenticated, as on a public repository
        self.alpha.init(["echo"])
        self.assertIn("alpha", anon.sync())

    def test_api_glob_pagination_and_prune(self) -> None:
        self.alpha.init(["echo"])
        for i in range(105):  # more than one page of matching refs
            self.github.git("update-ref", f"refs/heads/claude/pad-{i:03d}", self.github.head("main"))
        api = a2a.GitHubApi("o/r", api=self.github.url)
        api.fetch_peers(["claude/*"])
        self.assertIn("claude/alpha", api.peer_refs())
        self.assertEqual(len(api.peer_refs()), 106)
        api.fetch_peers(["claude/alpha"])  # exact ref, and the previous view is pruned
        self.assertEqual(list(api.peer_refs()), ["claude/alpha"])

    def test_github_repo_is_derived_from_remote_urls(self) -> None:
        for url in ("https://github.com/o/r.git", "git@github.com:o/r.git",
                    "http://local_proxy@127.0.0.1:1/git/o/r"):
            self.assertEqual(a2a.github_repo_of(url), "o/r")


class ProjectIndexTest(BusFixture):
    """Discovery through the Project v2 memory index, carried by the proxy transport."""

    def run_proxy(self, agent: a2a.Agent, records) -> dict:
        """Stand in for the push-triggered proxy Action: answer every pending request
        on the agent's ref with a receipt committed back onto that ref."""
        git = agent.git
        git.fetch_peers([agent.ref])
        tip = git.peer_refs()[agent.ref]
        pending = [n for n in git.ls(tip, a2a.REQUESTS_DIR + "/")
                   if git.show(tip, n.replace("requests/", "receipts/").replace(".json", ".receipt.json")) is None]
        files = {}
        for name in pending:
            request = json.loads(git.show(tip, name))
            request_id, operation = proxy.validate_request(request, "seanchatmangpt", 2)
            if operation == "memory.upsert":
                title, body, meta = proxy.normalize_record(request["payload"]["record"], None)
                records.append({"title": title, "body": body, "metadata": meta})
                result = {"action": "created", "record": records[-1]}
            else:
                result = {"records": [r for r in records if r["metadata"].get("kind") == request["payload"]["kind"]]}
            receipt = {"schema": "chatgpt-project-memory-receipt/v1", "request_id": request_id,
                       "operation": operation, "standing": "ALIVE", "result": result}
            files[f"{a2a.RECEIPTS_DIR}/{request_id}.receipt.json"] = json.dumps(receipt).encode()
        git.publish(agent.ref, "proxy", lambda base: (files, "receipt: Project v2 memory proxy", None))
        return files

    def test_index_announce_is_a_valid_proxy_request(self) -> None:
        self.alpha.init(["echo"])
        request = self.alpha.announce_index()
        request_id, operation = proxy.validate_request(request, "seanchatmangpt", 2)
        self.assertEqual(operation, "memory.upsert")
        record = request["payload"]["record"]
        self.assertEqual(record["key"], "a2a/agents/alpha")
        self.assertEqual(record["metadata"]["outbox_ref"], "claude/alpha")
        self.assertEqual(record["metadata"]["card_digest"], a2a.digest(self.alpha.card(["echo"])))
        self.assertEqual(record["standing"], "UNKNOWN")  # a pointer, never replay evidence
        tip = self.alpha.sync()["alpha"]["commit"]
        self.assertIsNotNone(self.alpha.git.show(tip, f"{a2a.REQUESTS_DIR}/{request_id}.json"))

    def test_index_reaches_a_ref_outside_the_listen_globs(self) -> None:
        records: list = []
        # epsilon lives on a branch no glob covers.
        eps = self.clone(Path(self.tmp.name) / "eps", "feature/epsilon")
        eps = a2a.Agent(eps.git, "epsilon", "feature/epsilon", ["claude/*"])
        eps.init(["echo"])
        eps.announce_index()
        self.run_proxy(eps, records)
        self.alpha.init(["echo"])
        self.assertNotIn("epsilon", self.alpha.sync())
        # a spoofed index entry pointing epsilon's name at the wrong ref, and junk refs
        records.append({"metadata": {"kind": a2a.INDEX_KIND, "outbox_ref": "claude/beta", "agent": "epsilon"}})
        records.append({"metadata": {"kind": a2a.INDEX_KIND, "outbox_ref": "../main"}})
        self.beta.init(["echo"])
        request = self.alpha.request_discovery()
        self.run_proxy(self.alpha, records)
        indexed = a2a.Agent(self.alpha.git, "alpha", "claude/alpha", ["claude/*"], use_index=True)
        tip = indexed.git.peer_refs()["claude/alpha"]
        self.assertEqual(indexed.discovery_receipt(tip, request["request_id"])["standing"], "ALIVE")
        self.assertEqual(indexed.index_refs(tip), ["claude/beta", "feature/epsilon"])
        agents = indexed.sync()
        self.assertEqual(agents["epsilon"]["ref"], "feature/epsilon")  # authority stays with the card's ref
        req = indexed.send("epsilon", "request", [{"kind": "text", "text": "found you"}], skill="echo")
        eps_view = a2a.Agent(eps.git, "epsilon", "feature/epsilon", ["claude/*"])
        self.assertEqual([r["in_reply_to"] for r in eps_view.serve_once()], [req["id"]])
        self.assertEqual(indexed.wait_reply(req["id"], timeout=0, interval=0)["responder_ref"], "feature/epsilon")

    def test_discover_without_proxy_receipt_is_unknown(self) -> None:
        self.alpha.init(["echo"])
        result = self.alpha.discover(timeout=0, interval=0)
        self.assertEqual(result["standing"], "UNKNOWN")

    def test_non_alive_receipt_contributes_no_refs(self) -> None:
        self.alpha.init(["echo"])
        request = self.alpha.request_discovery()
        receipt = {"standing": "BLOCKED", "reason": "IRREDUCIBLE_AUTHORITY",
                   "result": {"records": [{"metadata": {"kind": a2a.INDEX_KIND, "outbox_ref": "feature/x"}}]}}
        self.alpha.git.publish("claude/alpha", "proxy", lambda base: (
            {f"{a2a.RECEIPTS_DIR}/{request['request_id']}.receipt.json": json.dumps(receipt).encode()}, "r", None))
        tip = self.alpha.sync()["alpha"]["commit"]
        self.assertEqual(self.alpha.index_refs(tip), [])


if __name__ == "__main__":
    unittest.main()
