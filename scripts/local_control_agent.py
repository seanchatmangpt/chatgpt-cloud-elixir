#!/usr/bin/env python3
"""Bounded local-control agent for chatgpt-cloud-elixir.

The agent polls a dedicated Git branch for typed JSON requests, executes only
operations admitted by a local policy, and writes typed receipts back to the
transport branch. It deliberately does not expose an arbitrary shell.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Iterable, Mapping, Optional

DEFAULT_OPERATIONS = {
    "system.snapshot",
    "filesystem.list",
    "filesystem.read",
    "filesystem.write",
    "filesystem.mkdir",
    "filesystem.delete",
    "process.run",
    "macos.open",
    "macos.notify",
    "macos.applescript.named",
}


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


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def within(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            pass
    return False


def truncate_text(value: str, limit: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return value, False
    return encoded[:limit].decode("utf-8", errors="replace"), True


class Policy:
    def __init__(self, raw: Mapping[str, Any]):
        self.raw = dict(raw)
        self.machine_id = str(raw.get("machine_id") or socket.gethostname())
        self.allowed_operations = set(raw.get("allowed_operations") or DEFAULT_OPERATIONS)
        self.read_roots = [expand_path(p) for p in raw.get("read_roots", [])]
        self.write_roots = [expand_path(p) for p in raw.get("write_roots", [])]
        self.allowed_executables = set(raw.get("allowed_executables", []))
        self.allowed_apps = set(raw.get("allowed_apps", []))
        self.named_applescripts = dict(raw.get("named_applescripts", {}))
        self.allow_destructive = bool(raw.get("allow_destructive", False))
        self.max_timeout_seconds = int(raw.get("max_timeout_seconds", 600))
        self.max_output_bytes = int(raw.get("max_output_bytes", 100_000))
        self.repo = str(raw.get("repo", "seanchatmangpt/chatgpt-cloud-elixir"))
        self.branch = str(raw.get("branch", "local-control-bus"))
        # Operations that must be explicitly approved locally (see ApprovalStore)
        # before LocalExecutor ever runs them, regardless of what the static
        # policy checks above admit. Defaults to every operation except the
        # read-only system.snapshot. This field is policy-tightening only: it
        # can require approval for more operations than the default, never
        # fewer than "every mutating/actuating operation".
        configured = raw.get("require_approval_for")
        if configured is None:
            self.require_approval_for = set(DEFAULT_OPERATIONS) - {"system.snapshot"}
        else:
            self.require_approval_for = set(configured) | (
                set(DEFAULT_OPERATIONS) - {"system.snapshot"}
            )

    def requires_approval(self, operation: str) -> bool:
        return operation in self.require_approval_for

    @classmethod
    def load(cls, path: Path) -> "Policy":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def require_operation(self, operation: str) -> None:
        if operation not in self.allowed_operations:
            raise Refused("OPERATION_NOT_ALLOWED", operation)

    def require_read_path(self, path: Path) -> None:
        if not self.read_roots or not within(path, self.read_roots):
            raise Refused("READ_PATH_NOT_ALLOWED", str(path))

    def require_write_path(self, path: Path) -> None:
        if not self.write_roots or not within(path, self.write_roots):
            raise Refused("WRITE_PATH_NOT_ALLOWED", str(path))

    def require_executable(self, executable: str) -> str:
        candidate = shutil.which(executable) if os.path.sep not in executable else str(expand_path(executable))
        if not candidate:
            raise Refused("EXECUTABLE_NOT_FOUND", executable)
        resolved = str(Path(candidate).resolve())
        basename = Path(resolved).name
        if (
            executable not in self.allowed_executables
            and basename not in self.allowed_executables
            and resolved not in self.allowed_executables
        ):
            raise Refused("EXECUTABLE_NOT_ALLOWED", executable)
        return resolved


class LocalExecutor:
    def __init__(self, policy: Policy):
        self.policy = policy

    def execute(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        request_id = str(request.get("request_id", ""))
        operation = str(request.get("operation", ""))
        machine = request.get("machine") or {}
        target_machine = str(machine.get("id", ""))
        payload = request.get("payload") or {}

        if not request_id:
            raise Refused("MISSING_REQUEST_ID", "request_id is required")
        if target_machine not in {"*", self.policy.machine_id}:
            raise Refused(
                "MACHINE_SCOPE_VIOLATION",
                f"target={target_machine!r}, local={self.policy.machine_id!r}",
            )
        expires_at = request.get("expires_at")
        if expires_at and parse_utc(str(expires_at)) < dt.datetime.now(dt.timezone.utc):
            raise Refused("REQUEST_EXPIRED", str(expires_at))
        self.policy.require_operation(operation)

        handler_name = "op_" + operation.replace(".", "_")
        handler = getattr(self, handler_name, None)
        if handler is None:
            raise Refused("UNSUPPORTED_OPERATION", operation)
        return handler(payload)

    def op_system_snapshot(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "machine_id": self.policy.machine_id,
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cwd": str(Path.cwd()),
        }

    def op_filesystem_list(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        path = expand_path(str(payload["path"]))
        self.policy.require_read_path(path)
        if not path.is_dir():
            raise Refused("NOT_A_DIRECTORY", str(path))
        entries = []
        for item in sorted(path.iterdir(), key=lambda p: p.name):
            stat = item.lstat()
            entries.append(
                {
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file" if item.is_file() else "other",
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
        return {"path": str(path), "entries": entries}

    def op_filesystem_read(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        path = expand_path(str(payload["path"]))
        self.policy.require_read_path(path)
        max_bytes = min(
            int(payload.get("max_bytes", self.policy.max_output_bytes)),
            self.policy.max_output_bytes,
        )
        original = path.read_bytes()
        clipped = len(original) > max_bytes
        data = original[:max_bytes]
        return {
            "path": str(path),
            "content": data.decode("utf-8", errors="replace"),
            "bytes_returned": len(data),
            "truncated": clipped,
            "sha256": hashlib.sha256(original).hexdigest(),
        }

    def op_filesystem_write(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        path = expand_path(str(payload["path"]))
        self.policy.require_write_path(path)
        content = str(payload.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return {
            "path": str(path),
            "bytes": len(content.encode("utf-8")),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

    def op_filesystem_mkdir(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        path = expand_path(str(payload["path"]))
        self.policy.require_write_path(path)
        path.mkdir(
            parents=bool(payload.get("parents", True)),
            exist_ok=bool(payload.get("exist_ok", True)),
        )
        return {"path": str(path), "exists": path.is_dir()}

    def op_filesystem_delete(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if not self.policy.allow_destructive:
            raise Refused("DESTRUCTIVE_OPERATION_DISABLED", "filesystem.delete")
        path = expand_path(str(payload["path"]))
        self.policy.require_write_path(path)
        if not path.exists() and not path.is_symlink():
            return {"path": str(path), "deleted": False, "reason": "not_found"}
        if path.is_dir() and not path.is_symlink():
            if not bool(payload.get("recursive", False)):
                path.rmdir()
            else:
                shutil.rmtree(path)
        else:
            path.unlink()
        return {"path": str(path), "deleted": True}

    def op_process_run(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        argv = payload.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(v, str) for v in argv):
            raise Refused("INVALID_ARGV", "payload.argv must be a non-empty string array")
        executable = self.policy.require_executable(argv[0])
        default_cwd = self.policy.read_roots[0] if self.policy.read_roots else Path.cwd()
        cwd = expand_path(str(payload.get("cwd", default_cwd)))
        self.policy.require_read_path(cwd)
        timeout = min(
            max(1, int(payload.get("timeout_seconds", self.policy.max_timeout_seconds))),
            self.policy.max_timeout_seconds,
        )
        started = time.monotonic()
        completed = subprocess.run(
            [executable, *argv[1:]],
            cwd=str(cwd),
            shell=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=self._safe_env(),
        )
        duration_ms = round((time.monotonic() - started) * 1000)
        stdout, stdout_truncated = truncate_text(completed.stdout, self.policy.max_output_bytes)
        stderr, stderr_truncated = truncate_text(completed.stderr, self.policy.max_output_bytes)
        return {
            "argv": list(argv),
            "resolved_executable": executable,
            "cwd": str(cwd),
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "duration_ms": duration_ms,
        }

    def _safe_env(self) -> Dict[str, str]:
        keep = ("HOME", "PATH", "LANG", "LC_ALL", "TMPDIR", "USER", "SHELL")
        return {key: os.environ[key] for key in keep if key in os.environ}

    def _require_macos(self) -> None:
        if platform.system() != "Darwin":
            raise Refused("UNSUPPORTED_PLATFORM", "macOS operation requested on non-Darwin host")

    def op_macos_open(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_macos()
        mode = str(payload.get("mode", "path"))
        value = str(payload["value"])
        if mode == "app":
            if value not in self.policy.allowed_apps:
                raise Refused("APP_NOT_ALLOWED", value)
            argv = ["/usr/bin/open", "-a", value]
        elif mode == "path":
            path = expand_path(value)
            self.policy.require_read_path(path)
            argv = ["/usr/bin/open", str(path)]
        elif mode == "url":
            if not bool(self.policy.raw.get("allow_open_urls", False)):
                raise Refused("OPEN_URLS_DISABLED", value)
            if not (value.startswith("https://") or value.startswith("http://")):
                raise Refused("URL_SCHEME_NOT_ALLOWED", value)
            argv = ["/usr/bin/open", value]
        else:
            raise Refused("INVALID_OPEN_MODE", mode)
        subprocess.run(
            argv,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        return {"mode": mode, "value": value, "opened": True}

    def op_macos_notify(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_macos()
        title = str(payload.get("title", "ChatGPT local control"))
        message = str(payload.get("message", ""))
        script = "display notification " + json.dumps(message) + " with title " + json.dumps(title)
        subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=True,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        return {"notified": True, "title": title}

    def op_macos_applescript_named(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self._require_macos()
        script_id = str(payload["script_id"])
        script = self.policy.named_applescripts.get(script_id)
        if not script:
            raise Refused("APPLESCRIPT_NOT_ALLOWED", script_id)
        completed = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=self.policy.max_timeout_seconds,
        )
        stdout, stdout_truncated = truncate_text(completed.stdout, self.policy.max_output_bytes)
        stderr, stderr_truncated = truncate_text(completed.stderr, self.policy.max_output_bytes)
        return {
            "script_id": script_id,
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


class ReplayLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"executed": {}}

    def seen(self, request_id: str) -> bool:
        return request_id in self.data["executed"]

    def record(self, request_id: str, request_sha256: str, standing: str) -> None:
        self.data["executed"][request_id] = {
            "request_sha256": request_sha256,
            "standing": standing,
            "recorded_at": utc_now(),
        }
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, self.path)


class ApprovalStore:
    """Local-only human-approval gate.

    Deliberately lives under `state_dir`, never under the git checkout the
    agent syncs (`ensure_checkout`/`sync_checkout` only ever touch
    `checkout`). Nothing pushed to the transport branch can create, or even
    see, a file here -- `sync_checkout`'s `git reset --hard` never runs
    against this directory. A request is admitted for execution only if a
    human ran `approve <request_id>` on *this* machine, after `sync_checkout`
    already pulled the request text for them to read.
    """

    def __init__(self, path: Path):
        self.dir = path
        self.dir.mkdir(parents=True, exist_ok=True)

    def _marker(self, request_id: str, verdict: str) -> Path:
        safe = request_id.replace("/", "_")
        return self.dir / f"{safe}.{verdict}"

    def status(self, request_id: str) -> str:
        if self._marker(request_id, "approved").exists():
            return "approved"
        if self._marker(request_id, "denied").exists():
            return "denied"
        return "pending"

    def approve(self, request_id: str) -> None:
        denied = self._marker(request_id, "denied")
        if denied.exists():
            denied.unlink()
        self._marker(request_id, "approved").write_text(utc_now() + "\n", encoding="utf-8")

    def deny(self, request_id: str) -> None:
        approved = self._marker(request_id, "approved")
        if approved.exists():
            approved.unlink()
        self._marker(request_id, "denied").write_text(utc_now() + "\n", encoding="utf-8")

    def mark_notified(self, request_id: str) -> bool:
        """Returns True the first time this is called for a request_id (so the
        caller can fire exactly one local notification per pending request
        instead of one every poll cycle)."""
        marker = self._marker(request_id, "notified")
        if marker.exists():
            return False
        marker.write_text(utc_now() + "\n", encoding="utf-8")
        return True


def notify_pending_locally(request_id: str, operation: str) -> None:
    """Best-effort local OS notification. Never raises -- a notification
    failure must not block the approval workflow itself."""
    if platform.system() != "Darwin":
        return
    try:
        message = f"{operation} ({request_id}) is waiting for local approval"
        script = (
            "display notification "
            + json.dumps(message)
            + " with title "
            + json.dumps("ChatGPT local control: approval needed")
        )
        subprocess.run(
            ["/usr/bin/osascript", "-e", script],
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
    policy: Policy,
    result: Optional[Mapping[str, Any]] = None,
    *,
    standing: str,
    reason: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "receipt_version": 1,
        "request_id": request.get("request_id"),
        "request_sha256": request.get("_request_sha256") or sha256_json(request),
        "operation": request.get("operation"),
        "machine_id": policy.machine_id,
        "repo": policy.repo,
        "branch": policy.branch,
        "started_at": request.get("_started_at"),
        "completed_at": utc_now(),
        "standing": standing,
        "reason": reason,
        "error": error,
        "result": result,
    }


def run_request(path: Path, policy: Policy, ledger: ReplayLedger) -> Dict[str, Any]:
    request = json.loads(path.read_text(encoding="utf-8"))
    request_id = str(request.get("request_id", ""))
    if request_id != path.stem:
        raise Refused(
            "REQUEST_ID_PATH_MISMATCH",
            f"request_id={request_id!r}, path={path.stem!r}",
        )
    if ledger.seen(request_id):
        raise Refused("REPLAY_DETECTED", request_id)
    request["_request_sha256"] = sha256_json(request)
    request["_started_at"] = utc_now()
    executor = LocalExecutor(policy)
    try:
        result = executor.execute(request)
        standing = "ALIVE"
        receipt = make_receipt(request, policy, result, standing=standing)
    except Refused as exc:
        standing = "REFUSED"
        receipt = make_receipt(
            request,
            policy,
            standing=standing,
            reason=exc.reason,
            error=exc.detail,
        )
    except subprocess.TimeoutExpired as exc:
        standing = "BUILD_BROKEN"
        receipt = make_receipt(
            request,
            policy,
            standing=standing,
            reason="PROCESS_TIMEOUT",
            error=str(exc),
        )
    except Exception as exc:
        standing = "BUILD_BROKEN"
        receipt = make_receipt(
            request,
            policy,
            standing=standing,
            reason=type(exc).__name__,
            error=str(exc),
        )
    ledger.record(request_id, receipt["request_sha256"], standing)
    return receipt


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
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


def commit_receipt(checkout: Path, receipt_path: Path, request_id: str) -> None:
    git("add", str(receipt_path.relative_to(checkout)), cwd=checkout)
    git("commit", "-m", f"receipt(local-control): {request_id}", cwd=checkout)
    branch = git("branch", "--show-current", cwd=checkout).stdout.strip()
    for attempt in range(3):
        pushed = git("push", "origin", f"HEAD:{branch}", cwd=checkout, check=False)
        if pushed.returncode == 0:
            return
        if attempt == 2:
            raise RuntimeError(f"git push failed: {pushed.stderr}")
        git("pull", "--rebase", "origin", branch, cwd=checkout)


def process_pending(
    checkout: Path, policy: Policy, ledger: ReplayLedger, approvals: ApprovalStore
) -> int:
    requests_dir = checkout / "local-control" / "requests"
    receipts_dir = checkout / "local-control" / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for request_path in sorted(requests_dir.glob("*.json")):
        request_id = request_path.stem
        receipt_path = receipts_dir / f"{request_id}.receipt.json"
        if receipt_path.exists():
            continue

        try:
            raw = json.loads(request_path.read_text(encoding="utf-8"))
        except Exception:
            raw = None
        operation = str((raw or {}).get("operation", ""))

        if raw is not None and policy.requires_approval(operation):
            status = approvals.status(request_id)
            if status == "pending":
                if approvals.mark_notified(request_id):
                    notify_pending_locally(request_id, operation)
                # Not terminal: no receipt is written, so this request is
                # re-checked (not re-executed) on every subsequent poll until
                # a human approves or denies it locally.
                continue
            if status == "denied":
                raw["_request_sha256"] = sha256_json(raw)
                raw["_started_at"] = utc_now()
                receipt = make_receipt(
                    raw,
                    policy,
                    standing="REFUSED",
                    reason="LOCAL_APPROVAL_DENIED",
                    error=f"request {request_id} was explicitly denied locally",
                )
                receipt_path.write_text(
                    json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                commit_receipt(checkout, receipt_path, request_id)
                count += 1
                continue
            # status == "approved": fall through to normal execution below.

        try:
            receipt = run_request(request_path, policy, ledger)
        except Refused as exc:
            raw = json.loads(request_path.read_text(encoding="utf-8"))
            raw["_request_sha256"] = sha256_json(raw)
            raw["_started_at"] = utc_now()
            receipt = make_receipt(
                raw,
                policy,
                standing="REFUSED",
                reason=exc.reason,
                error=exc.detail,
            )
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        commit_receipt(checkout, receipt_path, request_id)
        count += 1
    return count


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


def _pending_requests(checkout: Path, policy: Policy, approvals: ApprovalStore) -> list[Dict[str, Any]]:
    requests_dir = checkout / "local-control" / "requests"
    receipts_dir = checkout / "local-control" / "receipts"
    out = []
    for request_path in sorted(requests_dir.glob("*.json")):
        request_id = request_path.stem
        if (receipts_dir / f"{request_id}.receipt.json").exists():
            continue
        try:
            raw = json.loads(request_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        operation = str(raw.get("operation", ""))
        if not policy.requires_approval(operation):
            continue
        if approvals.status(request_id) != "pending":
            continue
        out.append(raw)
    return out


def list_pending(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    checkout = expand_path(args.checkout)
    state_dir = expand_path(args.state_dir)
    approvals = ApprovalStore(state_dir / "approvals")
    if not (checkout / ".git").exists():
        ensure_checkout(checkout, policy)
    sync_checkout(checkout, policy)
    pending = _pending_requests(checkout, policy, approvals)
    print(json.dumps(pending, indent=2, sort_keys=True))
    return 0


def _find_request(checkout: Path, request_id: str) -> Optional[Dict[str, Any]]:
    path = checkout / "local-control" / "requests" / f"{request_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def approve(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    checkout = expand_path(args.checkout)
    state_dir = expand_path(args.state_dir)
    if not (checkout / ".git").exists():
        ensure_checkout(checkout, policy)
    sync_checkout(checkout, policy)
    request = _find_request(checkout, args.request_id)
    if request is None:
        print(f"REFUSED[REQUEST_NOT_FOUND]: no request {args.request_id!r} on {policy.branch}", file=sys.stderr)
        return 1
    print("About to approve this request for LOCAL EXECUTION:")
    print(json.dumps(request, indent=2, sort_keys=True))
    if not args.yes:
        answer = input(f"Approve {args.request_id!r} ({request.get('operation')})? [y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("Not approved.")
            return 1
    approvals = ApprovalStore(state_dir / "approvals")
    approvals.approve(args.request_id)
    print(f"Approved {args.request_id!r}. It will execute on the next poll cycle.")
    return 0


def deny(args: argparse.Namespace) -> int:
    state_dir = expand_path(args.state_dir)
    approvals = ApprovalStore(state_dir / "approvals")
    approvals.deny(args.request_id)
    print(f"Denied {args.request_id!r}. It will be refused (LOCAL_APPROVAL_DENIED) on the next poll cycle.")
    return 0


def validate(args: argparse.Namespace) -> int:
    policy = Policy.load(Path(args.policy))
    print(
        json.dumps(
            {
                "machine_id": policy.machine_id,
                "repo": policy.repo,
                "branch": policy.branch,
                "allowed_operations": sorted(policy.allowed_operations),
                "read_roots": [str(p) for p in policy.read_roots],
                "write_roots": [str(p) for p in policy.write_roots],
                "allowed_executables": sorted(policy.allowed_executables),
                "allow_destructive": policy.allow_destructive,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded ChatGPT local-control agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--policy", required=True)
    p_serve.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    p_serve.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    p_serve.add_argument("--poll-seconds", type=int, default=15)
    p_serve.add_argument("--once", action="store_true")
    p_serve.set_defaults(func=serve)

    p_validate = sub.add_parser("validate-policy")
    p_validate.add_argument("--policy", required=True)
    p_validate.set_defaults(func=validate)

    p_list_pending = sub.add_parser(
        "list-pending", help="Show requests awaiting local approval"
    )
    p_list_pending.add_argument("--policy", required=True)
    p_list_pending.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    p_list_pending.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    p_list_pending.set_defaults(func=list_pending)

    p_approve = sub.add_parser(
        "approve", help="Approve one pending request for local execution"
    )
    p_approve.add_argument("request_id")
    p_approve.add_argument("--policy", required=True)
    p_approve.add_argument("--checkout", default="~/.local/share/chatgpt-local-control/repo")
    p_approve.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    p_approve.add_argument(
        "--yes", action="store_true", help="Skip the interactive confirmation prompt"
    )
    p_approve.set_defaults(func=approve)

    p_deny = sub.add_parser("deny", help="Deny one pending request")
    p_deny.add_argument("request_id")
    p_deny.add_argument("--state-dir", default="~/.local/state/chatgpt-local-control")
    p_deny.set_defaults(func=deny)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
