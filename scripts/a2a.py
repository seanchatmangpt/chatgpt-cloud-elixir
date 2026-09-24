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

Skills are bounded and side-effect free (CONSTRUCT/VERIFY only); there is no
remote-exec skill and a message never grants ambient DO authority.
"""
from __future__ import annotations

import argparse
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
    if not isinstance(ref, str) or not REF_NAME.match(ref) or ".." in ref or ref.endswith((".lock", "/")):
        raise A2AError("REFUSED_MALFORMED", f"invalid ref {ref!r}")
    return ref


# --------------------------------------------------------------------------- #
# git transport


class Git:
    def __init__(self, repo: Path, remote: str):
        self.repo = repo
        self.remote = remote

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

    def remote_sha(self, ref: str) -> str | None:
        line = self.out("ls-remote", self.remote, f"refs/heads/{ref}")
        return line.split()[0] if line else None

    def fetch_peers(self, globs: list[str]) -> None:
        specs = [f"+refs/heads/{g}:{PEER_NS}{g}" for g in globs]
        # --prune keeps deleted branches from resurrecting stale agents.
        self.run("fetch", "--quiet", "--prune", "--no-tags", self.remote, *specs)

    def peer_refs(self) -> dict[str, str]:
        refs: dict[str, str] = {}
        for line in self.out("for-each-ref", "--format=%(objectname) %(refname)", PEER_NS).splitlines():
            sha, name = line.split(" ", 1)
            refs[name[len(PEER_NS):]] = sha
        return refs

    def ls(self, commit: str, prefix: str) -> list[str]:
        proc = self.run("ls-tree", "-r", "--name-only", commit, "--", prefix, check=False)
        return proc.stdout.decode().splitlines() if proc.returncode == 0 else []

    def show(self, commit: str, path: str) -> bytes | None:
        proc = self.run("cat-file", "blob", f"{commit}:{path}", check=False)
        return proc.stdout if proc.returncode == 0 else None

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
        delay = 1.0
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


def listen_set(globs: list[str], own: str | None) -> list[str]:
    """Peer globs plus our own ref, without two refspecs targeting one local ref."""
    out = sorted(set(globs))
    if own and not any(fnmatch.fnmatchcase(own, g) for g in out):
        out.append(own)
    return out


# --------------------------------------------------------------------------- #
# ledger: authoritative, verified view of every agent


def read_json(git: Git, commit: str, path: str) -> dict[str, Any] | None:
    raw = git.show(commit, path)
    if raw is None or len(raw) > MAX_MESSAGE_BYTES:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def verify_chain(agent: str, messages: list[dict[str, Any]]) -> None:
    prev = None
    for expected_seq, msg in enumerate(messages):
        if msg.get("schema") != SCHEMA or msg.get("from") != agent:
            raise A2AError("REFUSED_TAMPERED", f"{agent}#{expected_seq}: wrong schema/sender")
        if msg.get("seq") != expected_seq or msg.get("prev") != prev:
            raise A2AError("REFUSED_TAMPERED", f"{agent}#{expected_seq}: broken seq/prev chain")
        if msg.get("performative") not in PERFORMATIVES:
            raise A2AError("REFUSED_MALFORMED", f"{agent}#{expected_seq}: unknown performative")
        if seal(msg)["id"] != msg.get("id"):
            raise A2AError("REFUSED_TAMPERED", f"{agent}#{expected_seq}: content digest mismatch")
        prev = msg["id"]


def load_agent(git: Git, commit: str, agent: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    card = read_json(git, commit, card_path(agent))
    prefix = f"{ROOT}/{agent}/outbox/"
    names = sorted(p for p in git.ls(commit, prefix) if re.fullmatch(re.escape(prefix) + r"\d{8}\.json", p))
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
    def __init__(self, git: Git, agent: str, ref: str, peers: list[str]):
        self.git = git
        self.agent = check_agent_id(agent)
        self.ref = check_ref(ref)
        self.peers = peers

    def card(self, skills: list[str]) -> dict[str, Any]:
        return {
            "@context": CONTEXT,
            "type": "a2a:AgentCard",
            "schema": SCHEMA,
            "agent": self.agent,
            "outbox_ref": self.ref,
            "repository": self.git.out("remote", "get-url", self.git.remote),
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
        return ledger(self.git)

    def serve_once(self) -> list[dict[str, Any]]:
        agents = self.sync()
        me = agents.get(self.agent)
        if me is None:
            raise A2AError("BLOCKED", f"agent {self.agent} not announced on {self.ref}")
        answered = {m.get("in_reply_to") for m in me["messages"]}
        offered = {s["id"] for s in me["card"].get("skills", [])}
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

    def wait_reply(self, request_id: str, timeout: float, interval: float) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        while True:
            for view in self.sync().values():
                if view["standing"] != "ALIVE":
                    continue
                for msg in view["messages"]:
                    if msg.get("in_reply_to") == request_id:
                        return {"reply": msg, "responder_ref": view["ref"], "responder_commit": view["commit"]}
            if time.monotonic() >= deadline:
                return None
            time.sleep(interval)


# --------------------------------------------------------------------------- #
# CLI


def current_branch(git: Git) -> str:
    return git.out("rev-parse", "--abbrev-ref", "HEAD")


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
    args = ap.parse_args(argv)

    try:
        repo = Path(subprocess.run(["git", "-C", args.repo, "rev-parse", "--show-toplevel"],
                                   capture_output=True, check=True).stdout.decode().strip())
        git = Git(repo, args.remote)
        peers = [g.strip() for g in args.peers.split(",") if g.strip()]
        if args.cmd in ("peers", "log"):
            git.fetch_peers(listen_set(peers, args.ref))
            agents = ledger(git)
            if args.cmd == "peers":
                emit({a: {"ref": v["ref"], "commit": v["commit"], "standing": v["standing"],
                          "messages": len(v["messages"]),
                          "skills": [s["id"] for s in v["card"].get("skills", [])],
                          **({"detail": v["detail"]} if "detail" in v else {})} for a, v in agents.items()})
            else:
                msgs = [m for v in agents.values() for m in v["messages"]
                        if not args.conversation or m.get("conversation") == args.conversation]
                emit(sorted(msgs, key=lambda m: (m.get("created_at", ""), m["from"], m["seq"])))
            return 0
        if not args.agent:
            raise A2AError("REFUSED_MALFORMED", "--agent (or A2A_AGENT) is required")
        agent = Agent(git, args.agent, args.ref or current_branch(git), peers)
        if args.cmd == "init":
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
                got = agent.wait_reply(msg["id"], args.wait, args.interval)
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
