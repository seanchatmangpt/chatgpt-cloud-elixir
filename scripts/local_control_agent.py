#!/usr/bin/env python3
"""Approval-gated, Git-transported local capsule runner for macOS + Colima.

Track B intentionally exposes one remote operation only: ``process.run`` for
this repository's ``scripts/build-*.sh`` and ``scripts/verify-*.sh`` scripts.
The request never contains a shell command. The agent manufactures the exact
``colima ssh -- bash -lc ...`` command locally from a validated script path and
an out-of-repository local policy.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from typing import Any, Dict, Mapping, Optional

ALLOWED_OPERATION = "process.run"
SCRIPT_RE = re.compile(r"^scripts/(?:build|verify)-[A-Za-z0-9][A-Za-z0-9._-]*\.sh$")
TERMINAL_STANDINGS = {"ALIVE", "REFUSED", "BUILD_BROKEN", "UNKNOWN"}


class Refused(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def truncate_text(value: str, limit: int) -> tuple[str, bool, int, str]:
    encoded = value.encode("utf-8", errors="replace")
    digest = sha256_bytes(encoded)
    if len(encoded) <= limit:
        return value, False, len(encoded), digest
    return encoded[:limit].decode("utf-8", errors="replace"), True, len(encoded), digest


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def normalize_repo_remote(value: str) -> str:
    value = value.strip()
    if value.startswith("git@github.com:"):
        value = value[len("git@github.com:") :]
    elif "github.com/" in value:
        value = value.split("github.com/", 1)[1]
    return value.removesuffix(".git").strip("/")


class Policy:
    def __init__(self, raw: Mapping[str, Any]):
        self.raw = dict(raw)
        self.repo = str(raw.get("repo", "seanchatmangpt/chatgpt-cloud-elixir"))
        self.branch = str(raw.get("branch", "local-control-bus"))
        self.machine_id = str(raw.get("machine_id") or socket.gethostname())
        self.repo_root = expand_path(str(raw.get("repo_root", "~/Projects/chatgpt-cloud-elixir")))
        self.colima_executable = str(raw.get("colima_executable", "colima"))
        self.required_platform = str(raw.get("required_platform", "Darwin"))
        self.max_timeout_seconds = int(raw.get("max_timeout_seconds", 3600))
        self.max_output_bytes = int(raw.get("max_output_bytes", 1_000_000))
        allowed = raw.get("allowed_operations", [ALLOWED_OPERATION])
        self.allowed_operations = set(str(v) for v in allowed)
        if self.allowed_operations != {ALLOWED_OPERATION}:
            raise ValueError("Track B policy may allow only process.run")

    @classmethod
    def load(cls, path: Path) -> "Policy":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def require_platform(self) -> None:
        if self.required_platform and platform.system() != self.required_platform:
            raise Refused(
                "UNSUPPORTED_PLATFORM",
                f"required={self.required_platform!r}, actual={platform.system()!r}",
            )

    def resolve_colima(self) -> str:
        candidate = (
            shutil.which(self.colima_executable)
            if os.path.sep not in self.colima_executable
            else str(expand_path(self.colima_executable))
        )
        if not candidate or not Path(candidate).exists():
            raise Refused("COLIMA_NOT_AVAILABLE", self.colima_executable)
        return str(Path(candidate).resolve())

    def resolve_script(self, script: str) -> Path:
        if not SCRIPT_RE.fullmatch(script):
            raise Refused(
                "SCRIPT_NOT_ALLOWED",
                "only scripts/build-*.sh and scripts/verify-*.sh are admitted",
            )
        root = self.repo_root.resolve()
        candidate = (root / script).resolve()
        if not within(candidate, root):
            raise Refused("SCRIPT_PATH_ESCAPE", script)
        if not candidate.is_file():
            raise Refused("SCRIPT_NOT_FOUND", str(candidate))
        return candidate


class ReplayLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"terminal": {}}

    def seen(self, request_id: str) -> bool:
        return request_id in self.data["terminal"]

    def record(self, request_id: str, request_sha256: str, standing: str) -> None:
        self.data["terminal"][request_id] = {
            "request_sha256": request_sha256,
            "standing": standing,
            "recorded_at": utc_now(),
        }
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, self.path)


class ApprovalStore:
    """Local-only approval state, hash-bound to the exact request content."""

    def __init__(self, path: Path):
        self.dir = path
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe(request_id: str) -> str:
        return request_id.replace("/", "_")

    def _marker(self, request_id: str, verdict: str) -> Path:
        return self.dir / f"{self._safe(request_id)}.{verdict}.json"

    def _read_hash(self, request_id: str, verdict: str) -> Optional[str]:
        path = self._marker(request_id, verdict)
        if not path.exists():
            return None
        try:
            return str(json.loads(path.read_text(encoding="utf-8"))["request_sha256"])
        except Exception:
            return None

    def status(self, request_id: str, request_sha256: str) -> str:
        if self._read_hash(request_id, "approved") == request_sha256:
            return "approved"
        if self._read_hash(request_id, "denied") == request_sha256:
            return "denied"
        return "pending"

    def _write(self, request_id: str, verdict: str, request_sha256: str) -> None:
        opposite = "denied" if verdict == "approved" else "approved"
        other = self._marker(request_id, opposite)
        if other.exists():
            other.unlink()
        self._marker(request_id, verdict).write_text(
            json.dumps(
                {"request_id": request_id, "request_sha256": request_sha256, "at": utc_now()},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def approve(self, request_id: str, request_sha256: str) -> None:
        self._write(request_id, "approved", request_sha256)

    def deny(self, request_id: str, request_sha256: str) -> None:
        self._write(request_id, "denied", request_sha256)

    def mark_notified(self, request_id: str, request_sha256: str) -> bool:
        path = self.dir / f"{self._safe(request_id)}.notified.{request_sha256}.json"
        if path.exists():
            return False
        path.write_text(json.dumps({"at": utc_now()}) + "\n", encoding="utf-8")
        return True


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=check, capture_output=True, text=True
    )


def repository_identity(policy: Policy) -> Dict[str, Any]:
    root = policy.repo_root
    if not root.is_dir():
        raise Refused("REPO_ROOT_NOT_FOUND", str(root))
    try:
        top = Path(git("rev-parse", "--show-toplevel", cwd=root).stdout.strip()).resolve()
        head = git("rev-parse", "HEAD", cwd=root).stdout.strip()
        dirty_text = git("status", "--porcelain", cwd=root).stdout
        remote = git("config", "--get", "remote.origin.url", cwd=root, check=False).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise Refused("REPO_IDENTITY_UNAVAILABLE", str(exc)) from exc
    if top != root.resolve():
        raise Refused("REPO_ROOT_MISMATCH", f"configured={root}, actual={top}")
    if remote and normalize_repo_remote(remote) != policy.repo:
        raise Refused("REPO_REMOTE_MISMATCH", f"expected={policy.repo}, actual={remote}")
    return {
        "repo_root": str(root.resolve()),
        "head_sha": head,
        "dirty": bool(dirty_text.strip()),
        "remote": remote or None,
    }


def validate_request(path: Path, policy: Policy, ledger: Optional[ReplayLedger]) -> Dict[str, Any]:
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        raise Refused("INVALID_REQUEST", "top level must be an object")
    allowed_keys = {"request_id", "operation", "machine", "expires_at", "payload"}
    extra = set(request) - allowed_keys
    if extra:
        raise Refused("INVALID_REQUEST_FIELDS", ",".join(sorted(extra)))
    request_id = str(request.get("request_id", ""))
    if not request_id or request_id != path.stem:
        raise Refused("REQUEST_ID_PATH_MISMATCH", f"request_id={request_id!r}, path={path.stem!r}")
    if ledger is not None and ledger.seen(request_id):
        raise Refused("REPLAY_DETECTED", request_id)
    if request.get("operation") != ALLOWED_OPERATION:
        raise Refused("OPERATION_NOT_ALLOWED", str(request.get("operation")))
    machine = request.get("machine")
    if not isinstance(machine, dict) or set(machine) != {"id"}:
        raise Refused("INVALID_MACHINE", "machine must contain only id")
    target = str(machine.get("id", ""))
    if target != policy.machine_id:
        raise Refused("MACHINE_SCOPE_VIOLATION", f"target={target!r}, local={policy.machine_id!r}")
    expires_at = request.get("expires_at")
    if expires_at and parse_utc(str(expires_at)) < dt.datetime.now(dt.timezone.utc):
        raise Refused("REQUEST_EXPIRED", str(expires_at))
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise Refused("INVALID_PAYLOAD", "payload must be an object")
    if set(payload) - {"script", "timeout_seconds"}:
        raise Refused("INVALID_PAYLOAD_FIELDS", ",".join(sorted(set(payload) - {"script", "timeout_seconds"})))
    script = payload.get("script")
    if not isinstance(script, str):
        raise Refused("INVALID_SCRIPT", "payload.script must be a string")
    timeout = int(payload.get("timeout_seconds", policy.max_timeout_seconds))
    if timeout < 1 or timeout > policy.max_timeout_seconds:
        raise Refused("TIMEOUT_NOT_ALLOWED", str(timeout))
    policy.require_platform()
    policy.resolve_script(script)
    policy.resolve_colima()
    request_sha256 = sha256_json(request)
    return {"request": request, "request_sha256": request_sha256, "timeout_seconds": timeout}


def command_plan(admitted: Mapping[str, Any], policy: Policy) -> Dict[str, Any]:
    request = admitted["request"]
    script = str(request["payload"]["script"])
    script_path = policy.resolve_script(script)
    colima = policy.resolve_colima()
    repo = repository_identity(policy)
    relative_exec = "./" + script
    inner = f"cd -- {shlex.quote(repo['repo_root'])} && exec bash {shlex.quote(relative_exec)}"
    argv = [colima, "ssh", "--", "bash", "-lc", inner]
    script_bytes = script_path.read_bytes()
    return {
        "argv": argv,
        "literal_command": shlex.join(argv),
        "inner_command": inner,
        "script": script,
        "script_sha256": sha256_bytes(script_bytes),
        "repo": repo,
        "timeout_seconds": int(admitted["timeout_seconds"]),
    }


def notify_pending_locally(request_id: str, script: str) -> None:
    if platform.system() != "Darwin":
        return
    try:
        message = f"{script} ({request_id}) is waiting for local approval"
        script_text = (
            "display notification " + json.dumps(message) + " with title "
            + json.dumps("ChatGPT local control: approval needed")
        )
        subprocess.run(
            ["/usr/bin/osascript", "-e", script_text],
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        pass


def make_receipt(
    request: Mapping[str, Any],
    request_sha256: str,
    policy: Policy,
    *,
    standing: str,
    command: Optional[Mapping[str, Any]] = None,
    result: Optional[Mapping[str, Any]] = None,
    reason: Optional[str] = None,
    error: Optional[str] = None,
    started_at: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "receipt_version": 1,
        "request_id": request.get("request_id"),
        "request_sha256": request_sha256,
        "operation": request.get("operation"),
        "machine_id": policy.machine_id,
        "repo": policy.repo,
        "branch": policy.branch,
        "started_at": started_at,
        "completed_at": utc_now(),
        "standing": standing,
        "reason": reason,
        "error": error,
        "command": dict(command) if command is not None else None,
        "result": dict(result) if result is not None else None,
    }


def execute_admitted(admitted: Mapping[str, Any], policy: Policy) -> Dict[str, Any]:
    request = admitted["request"]
    request_sha256 = str(admitted["request_sha256"])
    plan = command_plan(admitted, policy)
    started_at = utc_now()
    started = time.monotonic()
    try:
        completed = subprocess.run(
            plan["argv"],
            cwd=plan["repo"]["repo_root"],
            shell=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=plan["timeout_seconds"],
            env={k: os.environ[k] for k in ("HOME", "PATH", "LANG", "LC_ALL", "TMPDIR", "USER", "SHELL") if k in os.environ},
        )
    except subprocess.TimeoutExpired as exc:
        return make_receipt(
            request,
            request_sha256,
            policy,
            standing="BUILD_BROKEN",
            command=plan,
            reason="PROCESS_TIMEOUT",
            error=str(exc),
            started_at=started_at,
        )
    except Exception as exc:
        return make_receipt(
            request,
            request_sha256,
            policy,
            standing="BUILD_BROKEN",
            command=plan,
            reason=type(exc).__name__,
            error=str(exc),
            started_at=started_at,
        )

    duration_ms = round((time.monotonic() - started) * 1000)
    stdout, stdout_truncated, stdout_bytes, stdout_sha256 = truncate_text(completed.stdout, policy.max_output_bytes)
    stderr, stderr_truncated, stderr_bytes, stderr_sha256 = truncate_text(completed.stderr, policy.max_output_bytes)
    result = {
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "duration_ms": duration_ms,
    }
    if completed.returncode == 0:
        return make_receipt(
            request,
            request_sha256,
            policy,
            standing="ALIVE",
            command=plan,
            result=result,
            started_at=started_at,
        )
    return make_receipt(
        request,
        request_sha256,
        policy,
        standing="BUILD_BROKEN",
        command=plan,
        result=result,
        reason="PROCESS_EXIT_NONZERO",
        error=f"command exited {completed.returncode}",
        started_at=started_at,
    )


def ensure_checkout(checkout: Path, policy: Policy) -> None:
    if checkout.exists() and (checkout / ".git").exists():
        return
    checkout.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "clone",
            "--single-branch",
            "--branch",
            policy.branch,
            f"https://github.com/{policy.repo}.git",
            str(checkout),
        ],
        check=True,
    )


def sync_checkout(checkout: Path, policy: Policy) -> None:
    git("fetch", "origin", policy.branch, cwd=checkout)
    git("checkout", policy.branch, cwd=checkout)
    git("reset", "--hard", f"origin/{policy.branch}", cwd=checkout)


def commit_receipt(checkout: Path, receipt_path: Path, request_id: str, standing: str) -> None:
    git("add", str(receipt_path.relative_to(checkout)), cwd=checkout)
    diff = git("diff", "--cached", "--quiet", cwd=checkout, check=False)
    if diff.returncode == 0:
        return
    git("commit", "-m", f"receipt(local-control): {request_id} {standing}", cwd=checkout)
    branch = git("branch", "--show-current", cwd=checkout).stdout.strip()
    for attempt in range(3):
        pushed = git("push", "origin", f"HEAD:{branch}", cwd=checkout, check=False)
        if pushed.returncode == 0:
            return
        if attempt == 2:
            raise RuntimeError(f"git push failed: {pushed.stderr}")
        git("pull", "--rebase", "origin", branch, cwd=checkout)


def load_receipt(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def persist_receipt(checkout: Path, receipt_path: Path, receipt: Mapping[str, Any]) -> None:
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    commit_receipt(checkout, receipt_path, str(receipt["request_id"]), str(receipt["standing"]))


def refused_receipt_for_path(path: Path, policy: Policy, exc: Refused) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    request_sha256 = sha256_json(raw)
    return make_receipt(
        raw,
        request_sha256,
        policy,
        standing="REFUSED",
        reason=exc.reason,
        error=exc.detail,
    )


def process_pending(
    checkout: Path, policy: Policy, ledger: ReplayLedger, approvals: ApprovalStore
) -> int:
    requests_dir = checkout / "local-control" / "requests"
    receipts_dir = checkout / "local-control" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    changed = 0
    for request_path in sorted(requests_dir.glob("*.json")):
        request_id = request_path.stem
        receipt_path = receipts_dir / f"{request_id}.receipt.json"
        existing = load_receipt(receipt_path)
        if existing and existing.get("standing") in TERMINAL_STANDINGS:
            continue

        try:
            admitted = validate_request(request_path, policy, ledger)
            plan = command_plan(admitted, policy)
        except Refused as exc:
            receipt = refused_receipt_for_path(request_path, policy, exc)
            persist_receipt(checkout, receipt_path, receipt)
            if receipt.get("request_id"):
                ledger.record(str(receipt["request_id"]), str(receipt["request_sha256"]), "REFUSED")
            changed += 1
            continue
        except Exception as exc:
            raw = json.loads(request_path.read_text(encoding="utf-8"))
            receipt = make_receipt(
                raw,
                sha256_json(raw),
                policy,
                standing="BUILD_BROKEN",
                reason=type(exc).__name__,
                error=str(exc),
            )
            persist_receipt(checkout, receipt_path, receipt)
            ledger.record(request_id, str(receipt["request_sha256"]), "BUILD_BROKEN")
            changed += 1
            continue

        request = admitted["request"]
        request_sha256 = str(admitted["request_sha256"])
        status = approvals.status(request_id, request_sha256)
        if status == "pending":
            pending = make_receipt(
                request,
                request_sha256,
                policy,
                standing="PENDING_APPROVAL",
                command=plan,
                reason="LOCAL_APPROVAL_REQUIRED",
                error="Run local_control_agent.py approve <request_id> after reviewing command.literal_command",
            )
            if not existing or existing.get("request_sha256") != request_sha256 or existing.get("standing") != "PENDING_APPROVAL":
                persist_receipt(checkout, receipt_path, pending)
                changed += 1
            if approvals.mark_notified(request_id, request_sha256):
                notify_pending_locally(request_id, str(request["payload"]["script"]))
            continue

        if status == "denied":
            receipt = make_receipt(
                request,
                request_sha256,
                policy,
                standing="REFUSED",
                command=plan,
                reason="LOCAL_APPROVAL_DENIED",
                error=f"request {request_id} was explicitly denied locally",
            )
            persist_receipt(checkout, receipt_path, receipt)
            ledger.record(request_id, request_sha256, "REFUSED")
            changed += 1
            continue

        receipt = execute_admitted(admitted, policy)
        persist_receipt(checkout, receipt_path, receipt)
        ledger.record(request_id, request_sha256, str(receipt["standing"]))
        changed += 1
    return changed


def _request_path(checkout: Path, request_id: str) -> Path:
    return checkout / "local-control" / "requests" / f"{request_id}.json"


def _load_current_request(checkout: Path, request_id: str, policy: Policy) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    path = _request_path(checkout, request_id)
    if not path.exists():
        raise Refused("REQUEST_NOT_FOUND", request_id)
    admitted = validate_request(path, policy, None)
    return admitted["request"], str(admitted["request_sha256"]), command_plan(admitted, policy)


def serve(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    checkout = expand_path(args.checkout)
    state_dir = expand_path(args.state_dir)
    ledger = ReplayLedger(state_dir / "executed.json")
    approvals = ApprovalStore(state_dir / "approvals")
    ensure_checkout(checkout, policy)
    while True:
        try:
            sync_checkout(checkout, policy)
            process_pending(checkout, policy, ledger, approvals)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"[local-control] {type(exc).__name__}: {exc}", file=sys.stderr)
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


def approve(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    checkout = expand_path(args.checkout)
    state_dir = expand_path(args.state_dir)
    if not (checkout / ".git").exists():
        ensure_checkout(checkout, policy)
    sync_checkout(checkout, policy)
    try:
        request, request_sha256, plan = _load_current_request(checkout, args.request_id, policy)
    except Refused as exc:
        print(f"REFUSED[{exc.reason}]: {exc.detail}", file=sys.stderr)
        return 1
    print("Request JSON:")
    print(json.dumps(request, indent=2, sort_keys=True))
    print("\nLiteral command that will execute after approval:")
    print(plan["literal_command"])
    print(f"\nrequest_sha256={request_sha256}")
    if not args.yes:
        answer = input(f"Approve exact request {args.request_id!r}? [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("Not approved.")
            return 1
    ApprovalStore(state_dir / "approvals").approve(args.request_id, request_sha256)
    print(f"Approved {args.request_id!r} at hash {request_sha256}. It will execute on the next poll.")
    return 0


def deny(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    checkout = expand_path(args.checkout)
    state_dir = expand_path(args.state_dir)
    if not (checkout / ".git").exists():
        ensure_checkout(checkout, policy)
    sync_checkout(checkout, policy)
    try:
        _, request_sha256, plan = _load_current_request(checkout, args.request_id, policy)
    except Refused as exc:
        print(f"REFUSED[{exc.reason}]: {exc.detail}", file=sys.stderr)
        return 1
    print("Literal command being denied:")
    print(plan["literal_command"])
    ApprovalStore(state_dir / "approvals").deny(args.request_id, request_sha256)
    print(f"Denied {args.request_id!r} at hash {request_sha256}.")
    return 0


def list_pending(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    checkout = expand_path(args.checkout)
    state_dir = expand_path(args.state_dir)
    if not (checkout / ".git").exists():
        ensure_checkout(checkout, policy)
    sync_checkout(checkout, policy)
    approvals = ApprovalStore(state_dir / "approvals")
    ledger = ReplayLedger(state_dir / "executed.json")
    out = []
    for path in sorted((checkout / "local-control" / "requests").glob("*.json")):
        try:
            admitted = validate_request(path, policy, ledger)
            request_id = str(admitted["request"]["request_id"])
            request_sha256 = str(admitted["request_sha256"])
            if approvals.status(request_id, request_sha256) == "pending":
                out.append(
                    {
                        "request": admitted["request"],
                        "request_sha256": request_sha256,
                        "literal_command": command_plan(admitted, policy)["literal_command"],
                    }
                )
        except Exception:
            continue
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def validate_policy(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    print(
        json.dumps(
            {
                "repo": policy.repo,
                "branch": policy.branch,
                "machine_id": policy.machine_id,
                "repo_root": str(policy.repo_root),
                "allowed_operations": sorted(policy.allowed_operations),
                "required_platform": policy.required_platform,
                "colima_executable": policy.colima_executable,
                "max_timeout_seconds": policy.max_timeout_seconds,
                "max_output_bytes": policy.max_output_bytes,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Approval-gated Colima capsule runner")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--policy", required=True)
    serve_p.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    serve_p.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    serve_p.add_argument("--poll-seconds", type=int, default=15)
    serve_p.add_argument("--once", action="store_true")
    serve_p.set_defaults(func=serve)

    validate_p = sub.add_parser("validate-policy")
    validate_p.add_argument("--policy", required=True)
    validate_p.set_defaults(func=validate_policy)

    pending_p = sub.add_parser("list-pending")
    pending_p.add_argument("--policy", required=True)
    pending_p.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    pending_p.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    pending_p.set_defaults(func=list_pending)

    approve_p = sub.add_parser("approve")
    approve_p.add_argument("request_id")
    approve_p.add_argument("--policy", required=True)
    approve_p.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    approve_p.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    approve_p.add_argument("--yes", action="store_true")
    approve_p.set_defaults(func=approve)

    deny_p = sub.add_parser("deny")
    deny_p.add_argument("request_id")
    deny_p.add_argument("--policy", required=True)
    deny_p.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    deny_p.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    deny_p.set_defaults(func=deny)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
