#!/usr/bin/env python3
"""Semantic A2A over git refs: an ngrok-shaped rendezvous for ephemeral instances.

Ephemeral cloud containers (Claude Code sessions, ChatGPT containers, CI runners)
cannot accept inbound connections, but they can all make outbound pushes and
fetches to GitHub. This module turns that into an agent-to-agent bus:

- every agent owns exactly one *outbox ref* (a branch it is already authorized to
  push); it never writes anyone else's ref, so there are no write races and the
  per-session push fence is respected;
- an agent speaks by committing ``a2a/agents/<id>/outbox/<seq>.json`` onto its
  outbox ref with git plumbing (no worktree, no checkout, no force push);
- peers listen by fetching refs matching ``--peers`` globs into ``refs/a2a/peers/``;
- messages are content-addressed (``id = sha256(canonical message)``) and
  hash-chained (``prev``); a reader refuses any chain that does not verify;
- an agent is authoritative only on the ref its card names, so copies of an
  agent's directory carried along on other branches are ignored (anti-spoof);
- replies are idempotent from the ledger itself: a request is answered iff the
  responder's own outbox has no message ``in_reply_to`` it, so a replacement
  container resumes without local state.

Two transports speak the same wire format:

- ``git`` (default): git plumbing against a local clone;
- ``api``: HTTPS-only GitHub REST (git data API), for peers that have no git
  binary or clone, e.g. a ChatGPT container. Writes are fast-forward-only ref
  updates, so the one-writer/no-force law is the same on both transports.

Discovery is branch globs (``--peers``) plus, optionally, the GitHub Project v2
memory index (``index`` / ``discover`` / ``--use-index``): agents upsert their
card digest into Project #2 through the existing project-memory proxy, and a
discovering agent fetches the refs the index names. The index is only a hint;
authority still comes from the card on its own ref.

Skills are bounded and side-effect free (CONSTRUCT/VERIFY only); there is no
remote-exec skill and a message never grants ambient DO authority.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import fnmatch
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

SCHEMA = "chatgpt-cloud-a2a/v1"
CONTEXT = "https://github.com/seanchatmangpt/chatgpt-cloud-elixir/a2a/context.jsonld"
ROOT = "a2a/agents"
PEER_NS = "refs/a2a/peers/"
DEFAULT_PEERS = ("claude/*", "a2a/*")
AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
REF_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,200}$")
PERFORMATIVES = {"request", "inform", "agree", "refuse", "failure"}
MAX_MESSAGE_BYTES = 64 * 1024
PUSH_ATTEMPTS = 6
PUSH_BACKOFF = 1.0
GITHUB_API = "https://api.github.com"
GITHUB_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
# Project v2 discovery index, carried by the project-memory proxy
# (project-memory/README.md). Hard-scoped exactly as the proxy is.
INDEX_PROJECT = {"owner": "seanchatmangpt", "number": 2}
INDEX_KIND = "a2a.agent_card"
REQUESTS_DIR = "project-memory/requests"
RECEIPTS_DIR = "project-memory/receipts"


class A2AError(Exception):
    """Typed refusal; ``standing`` uses the repository vocabulary."""

    def __init__(self, standing: str, detail: str):
        super().__init__(f"{standing}: {detail}")
        self.standing = standing
        self.detail = detail


# --------------------------------------------------------------------------- #
# canonical form


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical(obj)).hexdigest()


def seal(message: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in message.items() if k != "id"}
    return {**body, "id": digest(body)}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def outbox_path(agent: str, seq: int) -> str:
    return f"{ROOT}/{agent}/outbox/{seq:08d}.json"


def card_path(agent: str) -> str:
    return f"{ROOT}/{agent}/card.json"


def check_agent_id(agent: str) -> str:
    if not isinstance(agent, str) or not AGENT_ID.match(agent):
        raise A2AError("REFUSED_MALFORMED", f"invalid agent id {agent!r}")
    return agent


def check_ref(ref: str) -> str:
    """Refuse anything ``git check-ref-format`` would refuse (plus ``..``): a ref named by
    untrusted input (the index) must never reach a refspec git rejects, which would fail
    the whole fetch and with it every peer's view."""
    if (not isinstance(ref, str) or not REF_NAME.match(ref) or ".." in ref or "//" in ref
            or ref.endswith((".", "/"))
            or any(c.startswith(".") or c.endswith(".lock") for c in ref.split("/"))):
        raise A2AError("REFUSED_MALFORMED", f"invalid ref {ref!r}")
    return ref


def is_glob(ref: str) -> bool:
    return any(ch in ref for ch in "*?[")


def strict_json(raw: bytes) -> Any:
    """Parse JSON, refusing duplicate object keys: last-key-wins here and first-key-wins
    in another reader would make one sealed message mean two things."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate key {key!r}")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs)


# --------------------------------------------------------------------------- #
# git transport


class Git:
    def __init__(self, repo: Path, remote: str):
        self.repo = repo
        self.remote = remote
        # Commits and blobs are immutable: cache listings per commit and bytes per blob
        # so a poll costs O(new objects), not O(every message on the bus).
        self._trees: dict[str, dict[str, str]] = {}
        self._blobs: dict[str, bytes] = {}

    def run(self, *args: str, stdin: bytes | None = None, env: dict[str, str] | None = None,
            check: bool = True) -> subprocess.CompletedProcess[bytes]:
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            input=stdin,
            capture_output=True,
            env={**os.environ, **(env or {})},
        )
        if check and proc.returncode != 0:
            raise A2AError("BLOCKED", f"git {' '.join(args)} exited {proc.returncode}: "
                                      f"{proc.stderr.decode(errors='replace').strip()}")
        return proc

    def out(self, *args: str, **kw: Any) -> str:
        return self.run(*args, **kw).stdout.decode().strip()

    def repository(self) -> str:
        return self.out("remote", "get-url", self.remote)

    def remote_sha(self, ref: str) -> str | None:
        line = self.out("ls-remote", self.remote, f"refs/heads/{ref}")
        return line.split()[0] if line else None

    def fetch_peers(self, globs: list[str]) -> None:
        exact = [g for g in globs if not is_glob(g)]
        live: set[str] = set()
        if exact:
            # An exact refspec for a missing branch fails the whole fetch; ask first.
            for line in self.out("ls-remote", "--heads", self.remote, *[f"refs/heads/{g}" for g in exact]).splitlines():
                live.add(line.split("\t", 1)[1][len("refs/heads/"):])
        wanted = [g for g in globs if is_glob(g) or g in live]
        # Replace the view, like the API transport: drop refs that left the listen set
        # or whose branch is gone, so a deleted agent cannot stay ALIVE on a stale tip.
        for name in self.peer_refs():
            if name not in live and not any(is_glob(g) and fnmatch.fnmatchcase(name, g) for g in globs):
                self.run("update-ref", "-d", f"{PEER_NS}{name}")
        if wanted:
            specs = [f"+refs/heads/{g}:{PEER_NS}{g}" for g in wanted]
            # --prune keeps deleted branches from resurrecting stale agents.
            self.run("fetch", "--quiet", "--prune", "--no-tags", self.remote, *specs)

    def peer_refs(self) -> dict[str, str]:
        refs: dict[str, str] = {}
        for line in self.out("for-each-ref", "--format=%(objectname) %(refname)", PEER_NS).splitlines():
            sha, name = line.split(" ", 1)
            refs[name[len(PEER_NS):]] = sha
        return refs

    def _tree(self, commit: str, directory: str) -> dict[str, str]:
        key = f"{commit}:{directory}"
        if key not in self._trees:
            proc = self.run("ls-tree", "-r", "-z", commit, "--", directory or ".", check=False)
            entries: dict[str, str] = {}
            if proc.returncode == 0:
                for row in proc.stdout.decode().split("\0"):
                    if row:
                        meta, name = row.split("\t", 1)
                        _mode, kind, sha = meta.split()
                        if kind == "blob":
                            entries[name] = sha
            self._trees[key] = entries
        return self._trees[key]

    @staticmethod
    def _dir(path: str) -> str:
        return path[:path.rfind("/") + 1]

    def ls(self, commit: str, prefix: str) -> list[str]:
        """Paths under ``commit`` starting with ``prefix`` (a string prefix, as on the API)."""
        return sorted(p for p in self._tree(commit, self._dir(prefix)) if p.startswith(prefix))

    def prefetch(self, commit: str, paths: list[str]) -> None:
        """Load every uncached blob among ``paths`` with one ``cat-file --batch``."""
        want: list[str] = []
        for path in paths:
            sha = self._tree(commit, self._dir(path)).get(path)
            if sha and sha not in self._blobs and sha not in want:
                want.append(sha)
        if not want:
            return
        out = self.run("cat-file", "--batch", stdin=("\n".join(want) + "\n").encode()).stdout
        pos = 0
        for sha in want:
            end = out.index(b"\n", pos)
            header = out[pos:end].split()
            if len(header) != 3 or header[1] != b"blob":
                raise A2AError("BLOCKED", f"cat-file --batch: unexpected header {out[pos:end]!r}")
            size = int(header[2])
            self._blobs[sha] = out[end + 1:end + 1 + size]
            pos = end + 1 + size + 1

    def show(self, commit: str, path: str) -> bytes | None:
        sha = self._tree(commit, self._dir(path)).get(path)
        if sha is None:
            return None
        if sha not in self._blobs:
            self.prefetch(commit, [path])
        return self._blobs[sha]

    def commit_files(self, base: str, files: dict[str, bytes], subject: str, agent: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "GIT_INDEX_FILE": str(Path(tmp) / "index"),
                "GIT_AUTHOR_NAME": os.environ.get("GIT_AUTHOR_NAME", f"a2a:{agent}"),
                "GIT_AUTHOR_EMAIL": os.environ.get("GIT_AUTHOR_EMAIL", f"{agent}@a2a.invalid"),
                "GIT_COMMITTER_NAME": os.environ.get("GIT_COMMITTER_NAME", f"a2a:{agent}"),
                "GIT_COMMITTER_EMAIL": os.environ.get("GIT_COMMITTER_EMAIL", f"{agent}@a2a.invalid"),
            }
            self.run("read-tree", base, env=env)
            for path, data in files.items():
                blob = self.out("hash-object", "-w", "--stdin", stdin=data)
                self.run("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            tree = self.out("write-tree", env=env)
            return self.out("commit-tree", tree, "-p", base, "-m", subject, env=env)

    def publish(self, ref: str, agent: str, build: Callable[[str], tuple[dict[str, bytes], str, Any]]) -> Any:
        """Append to ``ref`` without force; rebuild from the new tip on every race."""
        delay = PUSH_BACKOFF
        for _ in range(PUSH_ATTEMPTS):
            base = self.remote_sha(ref)
            if base:
                self.run("fetch", "--quiet", "--no-tags", self.remote, f"refs/heads/{ref}")
            else:
                base = self.out("rev-parse", "HEAD")
            files, subject, result = build(base)
            commit = self.commit_files(base, files, subject, agent)
            push = self.run("push", "--quiet", self.remote, f"{commit}:refs/heads/{ref}", check=False)
            if push.returncode == 0:
                # Keep our own view current without waiting for the next fetch.
                self.run("update-ref", f"{PEER_NS}{ref}", commit)
                return result
            err = push.stderr.decode(errors="replace")
            if "rejected" not in err and "fetch first" not in err and "non-fast-forward" not in err:
                raise A2AError("BLOCKED", f"push to {ref} refused: {err.strip()}")
            time.sleep(delay)
            delay *= 2
        raise A2AError("BLOCKED", f"push to {ref} lost {PUSH_ATTEMPTS} races")


# --------------------------------------------------------------------------- #
# GitHub REST transport: the same bus for peers with HTTPS but no git


class GitHubApi:
    """Duck-types ``Git`` over the GitHub git data API (stdlib ``urllib`` only).

    Reads work unauthenticated on public repositories; writes need a token and are
    fast-forward-only ref updates (``force: false``), rebuilt on every race.
    """

    def __init__(self, repo: str, token: str | None = None, api: str = GITHUB_API, base: str | None = None):
        if not GITHUB_REPO.match(repo or ""):
            raise A2AError("REFUSED_MALFORMED", f"invalid GitHub repository {repo!r}; want owner/name")
        self.repo = repo
        self.token = token
        self.api = api.rstrip("/")
        self.base = base
        self._refs: dict[str, str] = {}
        self._trees: dict[str, dict[str, str]] = {}
        self._blobs: dict[str, bytes] = {}

    def request(self, method: str, path: str, body: Any = None, missing_ok: bool = False) -> Any:
        url = f"{self.api}/repos/{self.repo}" + (f"/{path}" if path else "")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "chatgpt-cloud-a2a"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            if exc.code == 404 and missing_ok:
                return None
            if exc.code in (409, 422):
                raise ApiConflict(f"{method} {path}: {exc.code} {detail}") from None
            if exc.code in (401, 403):
                raise A2AError("BLOCKED", f"{method} {path}: {exc.code} (GitHub authority: token "
                                          f"{'present' if self.token else 'absent'}) {detail}") from None
            raise A2AError("BLOCKED", f"{method} {path}: HTTP {exc.code} {detail}") from None
        except urllib.error.URLError as exc:
            raise A2AError("BLOCKED", f"{method} {path}: {exc.reason}") from None
        return json.loads(raw) if raw else None

    @staticmethod
    def _q(ref: str) -> str:
        return urllib.parse.quote(ref, safe="/")

    def repository(self) -> str:
        return f"https://github.com/{self.repo}"

    def remote_sha(self, ref: str) -> str | None:
        got = self.request("GET", f"git/ref/heads/{self._q(ref)}", missing_ok=True)
        # A non-matching prefix query returns a list; only an exact object is the ref.
        return got["object"]["sha"] if isinstance(got, dict) else None

    def default_base(self) -> str:
        branch = self.base or self.request("GET", "")["default_branch"]
        sha = self.remote_sha(branch)
        if not sha:
            raise A2AError("BLOCKED", f"base branch {branch!r} not found on {self.repo}")
        return sha

    def matching(self, prefix: str) -> dict[str, str]:
        refs: dict[str, str] = {}
        page = 1
        while True:
            # No trailing slash: some egress proxies refuse non-canonical paths, and
            # the caller re-filters with fnmatch anyway.
            stem = prefix.rstrip("/")
            path = "git/matching-refs/heads" + (f"/{self._q(stem)}" if stem else "")
            rows = self.request("GET", f"{path}?per_page=100&page={page}") or []
            for row in rows:
                refs[row["ref"][len("refs/heads/"):]] = row["object"]["sha"]
            if len(rows) < 100:
                return refs
            page += 1

    def fetch_peers(self, globs: list[str]) -> None:
        refs: dict[str, str] = {}
        for glob in globs:
            literal = re.split(r"[*?\[]", glob, maxsplit=1)[0]
            if literal == glob:  # an exact ref, not a pattern
                sha = self.remote_sha(glob)
                if sha:
                    refs[glob] = sha
                continue
            for name, sha in self.matching(literal).items():
                if fnmatch.fnmatchcase(name, glob):
                    refs[name] = sha
        self._refs = refs  # replace, like ``fetch --prune``

    def peer_refs(self) -> dict[str, str]:
        return dict(self._refs)

    def _tree(self, commit: str) -> dict[str, str]:
        if commit not in self._trees:
            tree = self.request("GET", f"git/commits/{commit}")["tree"]["sha"]
            listing = self.request("GET", f"git/trees/{tree}?recursive=1")
            if listing.get("truncated"):
                raise A2AError("BLOCKED", f"tree of {commit[:12]} truncated by the API")
            self._trees[commit] = {e["path"]: e["sha"] for e in listing["tree"] if e["type"] == "blob"}
        return self._trees[commit]

    def ls(self, commit: str, prefix: str) -> list[str]:
        return sorted(p for p in self._tree(commit) if p.startswith(prefix))

    def show(self, commit: str, path: str) -> bytes | None:
        sha = self._tree(commit).get(path)
        if sha is None:
            return None
        if sha not in self._blobs:
            blob = self.request("GET", f"git/blobs/{sha}")
            self._blobs[sha] = base64.b64decode(blob["content"]) if blob.get("encoding") == "base64" \
                else blob["content"].encode()
        return self._blobs[sha]

    def publish(self, ref: str, agent: str, build: Callable[[str], tuple[dict[str, bytes], str, Any]]) -> Any:
        """Same contract as ``Git.publish``: append without force, rebuild on every race."""
        delay = PUSH_BACKOFF
        for _ in range(PUSH_ATTEMPTS):
            base = self.remote_sha(ref)
            create = base is None
            if create:
                base = self.default_base()
            files, subject, result = build(base)
            base_tree = self.request("GET", f"git/commits/{base}")["tree"]["sha"]
            tree = self.request("POST", "git/trees", {
                "base_tree": base_tree,
                "tree": [{"path": path, "mode": "100644", "type": "blob", "content": data.decode("utf-8")}
                         for path, data in sorted(files.items())],
            })["sha"]
            ident = {"name": os.environ.get("GIT_AUTHOR_NAME", f"a2a:{agent}"),
                     "email": os.environ.get("GIT_AUTHOR_EMAIL", f"{agent}@a2a.invalid")}
            commit = self.request("POST", "git/commits", {"message": subject, "tree": tree, "parents": [base],
                                                          "author": ident})["sha"]
            try:
                if create:
                    self.request("POST", "git/refs", {"ref": f"refs/heads/{ref}", "sha": commit})
                else:
                    self.request("PATCH", f"git/refs/heads/{self._q(ref)}", {"sha": commit, "force": False})
            except ApiConflict:
                time.sleep(delay)
                delay *= 2
                continue
            self._refs[ref] = commit
            return result
        raise A2AError("BLOCKED", f"update of {ref} lost {PUSH_ATTEMPTS} races")


class ApiConflict(Exception):
    """409/422 from a ref write: someone else advanced the ref first."""


def listen_set(globs: list[str], own: str | None, extra: list[str] | None = None) -> list[str]:
    """Peer globs plus our own ref (and index-discovered refs), without two refspecs
    targeting one local ref."""
    out = sorted(set(globs))
    for ref in [own, *(extra or [])]:
        if ref and ref not in out and not any(fnmatch.fnmatchcase(ref, g) for g in out):
            out.append(ref)
    return out


# --------------------------------------------------------------------------- #
# ledger: authoritative, verified view of every agent


def read_json(git: Git, commit: str, path: str) -> dict[str, Any] | None:
    raw = git.show(commit, path)
    if raw is None or len(raw) > MAX_MESSAGE_BYTES:
        return None
    try:
        value = strict_json(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


MESSAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


def message_shape_problem(msg: dict[str, Any]) -> str | None:
    """The fields every reader dereferences must have the types ``send`` writes, so a
    correctly sealed but malformed message refuses its author instead of crashing readers."""
    to = msg.get("to")
    if not isinstance(to, str) or (to != "*" and not AGENT_ID.match(to)):
        return "to is not an agent id or '*'"
    if msg.get("skill") is not None and not isinstance(msg.get("skill"), str):
        return "skill is not a string"
    if not isinstance(msg.get("conversation"), str):
        return "conversation is not a string"
    reply_to = msg.get("in_reply_to")
    if reply_to is not None and (not isinstance(reply_to, str) or not MESSAGE_ID.match(reply_to)):
        return "in_reply_to is not a message id"
    if msg.get("prev") is not None and not MESSAGE_ID.match(str(msg.get("prev"))):
        return "prev is not a message id"
    parts = msg.get("parts")
    if not isinstance(parts, list) or not all(isinstance(p, dict) for p in parts):
        return "parts is not a list of objects"
    return None


def card_skills(card: Any) -> list[str]:
    """Skill ids a card offers; ``[]`` for a card whose skills are malformed."""
    skills = card.get("skills") if isinstance(card, dict) else None
    if not isinstance(skills, list) or not all(isinstance(s, dict) and isinstance(s.get("id"), str) for s in skills):
        return []
    return [s["id"] for s in skills]


def card_problem(card: dict[str, Any]) -> str | None:
    skills = card.get("skills", [])
    if not isinstance(skills, list) or not all(isinstance(s, dict) and isinstance(s.get("id"), str) for s in skills):
        return "card skills are not a list of {id}"
    return None


def verify_chain(agent: str, messages: list[dict[str, Any]]) -> None:
    prev = None
    for expected_seq, msg in enumerate(messages):
        if msg.get("schema") != SCHEMA or msg.get("from") != agent:
            raise A2AError("REFUSED_TAMPERED", f"{agent}#{expected_seq}: wrong schema/sender")
        seq = msg.get("seq")
        if type(seq) is not int:  # True == 1 and 1.0 == 1 in Python, not in other readers
            raise A2AError("REFUSED_MALFORMED", f"{agent}#{expected_seq}: seq is not an integer")
        if seq != expected_seq or msg.get("prev") != prev:
            raise A2AError("REFUSED_TAMPERED", f"{agent}#{expected_seq}: broken seq/prev chain")
        if msg.get("performative") not in PERFORMATIVES:
            raise A2AError("REFUSED_MALFORMED", f"{agent}#{expected_seq}: unknown performative")
        problem = message_shape_problem(msg)
        if problem:
            raise A2AError("REFUSED_MALFORMED", f"{agent}#{expected_seq}: {problem}")
        if seal(msg)["id"] != msg.get("id"):
            raise A2AError("REFUSED_TAMPERED", f"{agent}#{expected_seq}: content digest mismatch")
        prev = msg["id"]


def load_agent(git: Git, commit: str, agent: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    card = read_json(git, commit, card_path(agent))
    prefix = f"{ROOT}/{agent}/outbox/"
    names = sorted(p for p in git.ls(commit, prefix) if re.fullmatch(re.escape(prefix) + r"\d{8}\.json", p))
    prefetch = getattr(git, "prefetch", None)
    if prefetch:
        prefetch(commit, names)
    messages = []
    for name in names:
        msg = read_json(git, commit, name)
        if msg is None:
            raise A2AError("REFUSED_MALFORMED", f"{name} unreadable on {commit[:12]}")
        messages.append(msg)
    verify_chain(agent, messages)
    return card, messages


def ledger(git: Git) -> dict[str, dict[str, Any]]:
    """Map agent id -> {card, ref, messages, standing}, trusting only the card's own ref."""
    agents: dict[str, dict[str, Any]] = {}
    for ref, commit in sorted(git.peer_refs().items()):
        seen = {p.split("/")[2] for p in git.ls(commit, ROOT + "/") if p.count("/") >= 3}
        for agent in sorted(seen):
            if not AGENT_ID.match(agent):
                continue
            card = read_json(git, commit, card_path(agent))
            if not card or card.get("outbox_ref") != ref or card.get("agent") != agent:
                continue  # a copy carried on someone else's branch: not authoritative here
            try:
                problem = card_problem(card)
                if problem:
                    raise A2AError("REFUSED_MALFORMED", f"{agent}: {problem}")
                _, messages = load_agent(git, commit, agent)
                agents[agent] = {"card": card, "ref": ref, "commit": commit, "messages": messages,
                                 "standing": "ALIVE"}
            except A2AError as exc:
                agents[agent] = {"card": card, "ref": ref, "commit": commit, "messages": [],
                                 "standing": exc.standing, "detail": exc.detail}
    return agents


# --------------------------------------------------------------------------- #
# skills: bounded, side-effect free


def observe() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "pid": os.getpid(),
        "session": os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID"),
        "observed_at": now(),
    }


def text_of(msg: dict[str, Any]) -> str:
    return "".join(p.get("text", "") for p in msg.get("parts", []) if isinstance(p, dict) and p.get("kind") == "text")


def skill_ping(msg: dict[str, Any], card: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"kind": "data", "data": {"pong": True, "environment": observe()}}]


def skill_echo(msg: dict[str, Any], card: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"kind": "text", "text": text_of(msg)}]


def skill_digest(msg: dict[str, Any], card: dict[str, Any]) -> list[dict[str, Any]]:
    text = text_of(msg)
    return [{"kind": "data", "data": {"sha256": hashlib.sha256(text.encode()).hexdigest(), "bytes": len(text.encode())}}]


def skill_describe(msg: dict[str, Any], card: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"kind": "data", "data": card}]


SKILLS: dict[str, tuple[str, Callable[[dict[str, Any], dict[str, Any]], list[dict[str, Any]]]]] = {
    "ping": ("Liveness plus an observation of the answering environment.", skill_ping),
    "echo": ("Return the request's text parts verbatim.", skill_echo),
    "digest": ("SHA-256 of the request's text parts.", skill_digest),
    "describe": ("Return this agent's card.", skill_describe),
}


# --------------------------------------------------------------------------- #
# agent operations


class Agent:
    def __init__(self, git: Git | GitHubApi, agent: str, ref: str, peers: list[str], use_index: bool = False):
        self.git = git
        self.agent = check_agent_id(agent)
        self.ref = check_ref(ref)
        self.peers = peers
        self.use_index = use_index

    def card(self, skills: list[str]) -> dict[str, Any]:
        return {
            "@context": CONTEXT,
            "type": "a2a:AgentCard",
            "schema": SCHEMA,
            "agent": self.agent,
            "outbox_ref": self.ref,
            "repository": self.git.repository(),
            "skills": [{"id": s, "description": SKILLS[s][0]} for s in skills],
            "authority": "CONSTRUCT_VERIFY; no remote exec; messages grant no ambient DO authority",
        }

    def _chain(self, base: str) -> list[dict[str, Any]]:
        return load_agent(self.git, base, self.agent)[1]

    def init(self, skills: list[str]) -> dict[str, Any]:
        unknown = [s for s in skills if s not in SKILLS]
        if unknown:
            raise A2AError("UNSUPPORTED", f"unknown skills {unknown}")
        card = self.card(skills)

        def build(base: str) -> tuple[dict[str, bytes], str, Any]:
            self._chain(base)  # refuse to announce on top of a corrupt chain
            return {card_path(self.agent): json.dumps(card, indent=2, sort_keys=True).encode() + b"\n"}, \
                f"a2a({self.agent}): announce card", card

        return self.git.publish(self.ref, self.agent, build)

    def send(self, to: str, performative: str, parts: list[dict[str, Any]], skill: str | None = None,
             conversation: str | None = None, in_reply_to: str | None = None) -> dict[str, Any]:
        if performative not in PERFORMATIVES:
            raise A2AError("REFUSED_MALFORMED", f"unknown performative {performative!r}")
        if to != "*":
            check_agent_id(to)

        def build(base: str) -> tuple[dict[str, bytes], str, Any]:
            if read_json(self.git, base, card_path(self.agent)) is None:
                raise A2AError("BLOCKED", f"agent {self.agent} has no card on {self.ref}; run init first")
            chain = self._chain(base)
            msg = seal({
                "@context": CONTEXT,
                "type": "a2a:Message",
                "schema": SCHEMA,
                "from": self.agent,
                "to": to,
                "seq": len(chain),
                "prev": chain[-1]["id"] if chain else None,
                "conversation": conversation or f"{self.agent}:{len(chain)}",
                "in_reply_to": in_reply_to,
                "performative": performative,
                "skill": skill,
                "parts": parts,
                "created_at": now(),
            })
            raw = json.dumps(msg, indent=2, sort_keys=True).encode() + b"\n"
            if len(raw) > MAX_MESSAGE_BYTES:
                raise A2AError("REFUSED_MALFORMED", "message exceeds 64 KiB")
            return {outbox_path(self.agent, msg["seq"]): raw}, \
                f"a2a({self.agent}): {performative} {skill or ''} -> {to} #{msg['seq']}", msg

        return self.git.publish(self.ref, self.agent, build)

    def sync(self) -> dict[str, dict[str, Any]]:
        self.git.fetch_peers(listen_set(self.peers, self.ref))
        if self.use_index:
            own = self.git.peer_refs().get(self.ref)
            extra = self.index_refs(own) if own else []
            if extra:
                self.git.fetch_peers(listen_set(self.peers, self.ref, extra))
        return ledger(self.git)

    # ---- Project v2 discovery index ------------------------------------- #
    # The index lives in GitHub Project #2 and is reached only through the
    # project-memory proxy: we commit a request file onto our own outbox ref, the
    # push-triggered proxy Action executes it and commits the receipt back onto
    # the same ref. The index is a *hint* for which refs to fetch; a card is still
    # authoritative only on the ref it names (``ledger``).

    def _request(self, verb: str, operation: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        request_id = f"a2a-{self.agent}-{verb}-{stamp}"
        return request_id, {"request_id": request_id, "operation": operation,
                            "project": dict(INDEX_PROJECT), "payload": payload}

    def announce_index(self) -> dict[str, Any]:
        """Upsert this agent's card digest into the Project v2 index (via the proxy)."""
        def build(base: str) -> tuple[dict[str, bytes], str, Any]:
            card = read_json(self.git, base, card_path(self.agent))
            if card is None:
                raise A2AError("BLOCKED", f"agent {self.agent} has no card on {self.ref}; run init first")
            request_id, request = self._request("index", "memory.upsert", {"record": {
                "key": f"a2a/agents/{self.agent}",
                "title": f"A2A agent {self.agent}",
                "kind": INDEX_KIND,
                # The record is a pointer, not replay evidence: readers verify the ref.
                "standing": "UNKNOWN",
                "repo": card.get("repository"),
                "ref": self.ref,
                "head_sha": base,
                "authority": card.get("authority"),
                "tags": ["a2a", "agent-card"],
                "body": f"A2A agent `{self.agent}` answers on ref `{self.ref}`. "
                        f"Verify its card at `{card_path(self.agent)}` on that ref before trusting it.",
                "metadata": {"agent": self.agent, "outbox_ref": self.ref, "schema": SCHEMA,
                             "card_digest": digest(card),
                             "skills": [sk.get("id") for sk in card.get("skills", [])]},
            }})
            return {f"{REQUESTS_DIR}/{request_id}.json": json.dumps(request, indent=2, sort_keys=True).encode()
                    + b"\n"}, f"a2a({self.agent}): index card in Project v2", request

        return self.git.publish(self.ref, self.agent, build)

    def request_discovery(self) -> dict[str, Any]:
        """Ask the proxy to query the index; the receipt lands on our own ref."""
        request_id, request = self._request("discover", "memory.query", {"kind": INDEX_KIND, "limit": 500})
        raw = json.dumps(request, indent=2, sort_keys=True).encode() + b"\n"
        return self.git.publish(self.ref, self.agent, lambda base: (
            {f"{REQUESTS_DIR}/{request_id}.json": raw}, f"a2a({self.agent}): discover via Project v2", request))

    def discovery_receipt(self, commit: str, request_id: str | None = None) -> dict[str, Any] | None:
        prefix = f"{RECEIPTS_DIR}/a2a-{self.agent}-discover-"
        names = [n for n in self.git.ls(commit, prefix) if n.endswith(".receipt.json")]
        if request_id:
            names = [n for n in names if n == f"{RECEIPTS_DIR}/{request_id}.receipt.json"]
        for name in sorted(names, reverse=True):
            raw = self.git.show(commit, name)
            try:
                receipt = json.loads(raw) if raw else None
            except ValueError:
                continue
            if isinstance(receipt, dict):
                return receipt
        return None

    def index_refs(self, commit: str) -> list[str]:
        """Outbox refs named by the newest ALIVE discovery receipt on our own ref."""
        receipt = self.discovery_receipt(commit)
        if not receipt or receipt.get("standing") != "ALIVE":
            return []
        refs = []
        for record in (receipt.get("result") or {}).get("records") or []:
            meta = record.get("metadata") if isinstance(record, dict) else None
            if not isinstance(meta, dict):
                continue
            ref = meta.get("outbox_ref")
            if meta.get("kind") != INDEX_KIND or not isinstance(ref, str):
                continue
            try:
                refs.append(check_ref(ref))  # index content is untrusted input
            except A2AError:
                continue
        return sorted(set(refs) - {self.ref})

    def discover(self, timeout: float, interval: float) -> dict[str, Any]:
        request = self.request_discovery()
        deadline = time.monotonic() + timeout
        while True:
            self.git.fetch_peers(listen_set(self.peers, self.ref))
            own = self.git.peer_refs().get(self.ref)
            receipt = self.discovery_receipt(own, request["request_id"]) if own else None
            if receipt is not None or time.monotonic() >= deadline:
                break
            time.sleep(interval)
        if receipt is None:
            return {"request": request["request_id"], "standing": "UNKNOWN",
                    "detail": "no proxy receipt yet; the Project v2 memory proxy Action has not answered"}
        return {"request": request["request_id"], "standing": receipt.get("standing"),
                "reason": receipt.get("reason"), "refs": self.index_refs(own) if own else []}

    def serve_once(self) -> list[dict[str, Any]]:
        agents = self.sync()
        me = agents.get(self.agent)
        if me is None:
            raise A2AError("BLOCKED", f"agent {self.agent} not announced on {self.ref}")
        if me["standing"] != "ALIVE":
            # An empty verified chain would re-answer every request; refuse instead.
            raise A2AError(me["standing"], f"own chain on {self.ref}: {me.get('detail')}")
        answered = {m.get("in_reply_to") for m in me["messages"]}
        offered = set(card_skills(me["card"]))
        replies = []
        for peer, view in sorted(agents.items()):
            if peer == self.agent or view["standing"] != "ALIVE":
                continue
            for msg in view["messages"]:
                if msg["performative"] != "request" or msg["to"] not in (self.agent, "*"):
                    continue
                if msg["id"] in answered:
                    continue
                skill = msg.get("skill")
                if skill not in offered:
                    perf, parts = "refuse", [{"kind": "data", "data": {"standing": "UNSUPPORTED", "skill": skill}}]
                else:
                    try:
                        perf, parts = "inform", SKILLS[skill][1](msg, me["card"])
                    except Exception as exc:  # a skill failure is reported, never swallowed
                        perf, parts = "failure", [{"kind": "data", "data": {"error": repr(exc)}}]
                reply = self.send(peer, perf, parts, skill=skill, conversation=msg.get("conversation"),
                                  in_reply_to=msg["id"])
                answered.add(msg["id"])
                replies.append(reply)
        return replies

    def wait_reply(self, request_id: str, timeout: float, interval: float,
                   responder: str | None = None) -> dict[str, Any] | None:
        """The first verified reply to ``request_id``: a non-request message addressed to
        us and, when ``responder`` is given (a unicast request), sent by that agent only,
        so a third party cannot answer on the addressee's behalf."""
        deadline = time.monotonic() + timeout
        while True:
            for peer, view in sorted(self.sync().items()):
                if view["standing"] != "ALIVE" or (responder not in (None, "*") and peer != responder):
                    continue
                for msg in view["messages"]:
                    if (msg.get("in_reply_to") == request_id and msg.get("performative") != "request"
                            and msg.get("to") in (self.agent, "*")):
                        return {"reply": msg, "responder_ref": view["ref"], "responder_commit": view["commit"]}
            if time.monotonic() >= deadline:
                return None
            time.sleep(interval)


# --------------------------------------------------------------------------- #
# CLI


def current_branch(git: Git) -> str:
    return git.out("rev-parse", "--abbrev-ref", "HEAD")


def github_repo_of(url: str) -> str | None:
    """owner/name from a GitHub remote URL (https, ssh, or a git proxy path)."""
    m = re.search(r"github\.com[:/]+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$", url) \
        or re.search(r"/git/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def make_transport(args: argparse.Namespace) -> tuple[Git | GitHubApi, Git | None]:
    git = None
    top = subprocess.run(["git", "-C", args.repo, "rev-parse", "--show-toplevel"], capture_output=True)
    if top.returncode == 0:
        git = Git(Path(top.stdout.decode().strip()), args.remote)
    if args.transport == "git":
        if git is None:
            raise A2AError("BLOCKED", f"{args.repo} is not a git checkout; use --transport api")
        return git, git
    repo = args.github_repo or (github_repo_of(git.repository()) if git else None)
    if not repo:
        raise A2AError("REFUSED_MALFORMED", "--github-repo owner/name is required for --transport api")
    token = next((os.environ[k] for k in ("A2A_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN") if os.environ.get(k)), None)
    return GitHubApi(repo, token=token, api=args.github_api, base=args.base), git


def emit(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--agent", default=os.environ.get("A2A_AGENT"))
    ap.add_argument("--ref", default=os.environ.get("A2A_REF"), help="outbox branch (default: current branch)")
    ap.add_argument("--peers", default=os.environ.get("A2A_PEERS", ",".join(DEFAULT_PEERS)),
                    help="comma-separated branch globs to listen on")
    ap.add_argument("--transport", choices=("git", "api"), default=os.environ.get("A2A_TRANSPORT", "git"),
                    help="git: local clone; api: HTTPS-only GitHub REST (no git binary or clone needed)")
    ap.add_argument("--github-repo", default=os.environ.get("A2A_GITHUB_REPO"),
                    help="owner/name for --transport api (default: derived from the git remote)")
    ap.add_argument("--github-api", default=os.environ.get("A2A_GITHUB_API", GITHUB_API))
    ap.add_argument("--base", default=os.environ.get("A2A_BASE"),
                    help="--transport api: branch a new outbox ref starts from (default: repo default branch)")
    ap.add_argument("--use-index", action="store_true", default=os.environ.get("A2A_USE_INDEX") == "1",
                    help="also listen on refs named by the newest Project v2 discovery receipt")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="announce this agent's card on its outbox ref")
    p.add_argument("--skills", default=",".join(SKILLS))
    p = sub.add_parser("send", help="send a request/inform to a peer")
    p.add_argument("--to", required=True)
    p.add_argument("--skill")
    p.add_argument("--performative", default="request")
    p.add_argument("--text", default="")
    p.add_argument("--data", help="JSON value to attach as a data part")
    p.add_argument("--wait", type=float, default=0, help="seconds to wait for the reply")
    p.add_argument("--interval", type=float, default=10)
    p = sub.add_parser("serve", help="answer requests addressed to this agent")
    p.add_argument("--once", action="store_true")
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--interval", type=float, default=10)
    sub.add_parser("peers", help="list verified agents visible on the bus")
    p = sub.add_parser("log", help="dump the verified conversation ledger")
    p.add_argument("--conversation")
    sub.add_parser("index", help="upsert this agent's card into the Project v2 discovery index")
    p = sub.add_parser("discover", help="query the Project v2 index; the proxy receipt lands on our ref")
    p.add_argument("--wait", type=float, default=600, help="seconds to wait for the proxy receipt")
    p.add_argument("--interval", type=float, default=15)
    args = ap.parse_args(argv)

    try:
        git, local = make_transport(args)
        peers = [g.strip() for g in args.peers.split(",") if g.strip()]
        if args.cmd in ("peers", "log"):
            if args.agent and args.use_index:
                ref = args.ref or (current_branch(local) if local else None)
                agents = Agent(git, args.agent, check_ref(ref or ""), peers, use_index=True).sync()
            else:
                git.fetch_peers(listen_set(peers, args.ref))
                agents = ledger(git)
            if args.cmd == "peers":
                emit({a: {"ref": v["ref"], "commit": v["commit"], "standing": v["standing"],
                          "messages": len(v["messages"]),
                          "skills": card_skills(v["card"]),
                          **({"detail": v["detail"]} if "detail" in v else {})} for a, v in agents.items()})
            else:
                msgs = [m for v in agents.values() for m in v["messages"]
                        if not args.conversation or m.get("conversation") == args.conversation]
                emit(sorted(msgs, key=lambda m: (m.get("created_at", ""), m["from"], m["seq"])))
            return 0
        if not args.agent:
            raise A2AError("REFUSED_MALFORMED", "--agent (or A2A_AGENT) is required")
        ref = args.ref or (current_branch(local) if local and args.transport == "git" else None)
        if not ref:
            raise A2AError("REFUSED_MALFORMED", "--ref (or A2A_REF) is required with --transport api")
        agent = Agent(git, args.agent, ref, peers, use_index=args.use_index)
        if args.cmd == "index":
            emit(agent.announce_index())
        elif args.cmd == "discover":
            result = agent.discover(args.wait, args.interval)
            emit(result)
            return 0 if result["standing"] == "ALIVE" else 3
        elif args.cmd == "init":
            emit(agent.init([s.strip() for s in args.skills.split(",") if s.strip()]))
        elif args.cmd == "send":
            parts: list[dict[str, Any]] = []
            if args.text:
                parts.append({"kind": "text", "text": args.text})
            if args.data:
                parts.append({"kind": "data", "data": json.loads(args.data)})
            msg = agent.send(args.to, args.performative, parts, skill=args.skill)
            result: dict[str, Any] = {"sent": msg}
            if args.wait > 0:
                got = agent.wait_reply(msg["id"], args.wait, args.interval, responder=msg["to"])
                result["reply"] = got
                result["standing"] = "ALIVE" if got else "UNKNOWN"
            emit(result)
            return 0 if args.wait <= 0 or result["reply"] else 3
        elif args.cmd == "serve":
            deadline = time.monotonic() + args.timeout
            while True:
                for reply in agent.serve_once():
                    emit({"replied": reply["in_reply_to"], "to": reply["to"], "performative": reply["performative"],
                          "id": reply["id"]})
                    sys.stdout.flush()
                if args.once or time.monotonic() >= deadline:
                    break
                time.sleep(args.interval)
        return 0
    except A2AError as exc:
        emit({"standing": exc.standing, "detail": exc.detail})
        return 2


if __name__ == "__main__":
    sys.exit(main())
