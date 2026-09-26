#!/usr/bin/env python3
"""Bounded relay worker for XaaS gall-work lease descriptors.

The relay does not create a new execution API and never shells out. Its only
consequential adapter is the existing, fixed `zcode gall-work --lease ... --json`
lifecycle, which still claims/admit/closes through XaaS. `--allow-do` only
opens this local path; it is not authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

STATE_SCHEMA = "chatgpt-cloud.xaas-relay-state/1"
DESCRIPTOR_SCHEMA = "gall.work-lease/1"
RESULT_SCHEMA = "gall.work-result/1"
ENVELOPE_SCHEMA = "xaas.remote-relay-envelope/1"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
WORKER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_descriptor(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != DESCRIPTOR_SCHEMA:
        raise ValueError("DESCRIPTOR_SCHEMA")
    required = (
        "work_order_iri",
        "checkpoint_iri",
        "graph_digest",
        "repository_identity",
        "base_sha",
        "epoch_id",
        "worker_id",
        "worktree",
    )
    for field in required:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"DESCRIPTOR_FIELD:{field}")
    if ":" not in value["work_order_iri"] or ":" not in value["checkpoint_iri"]:
        raise ValueError("DESCRIPTOR_IRI")
    if not SHA256.fullmatch(value["graph_digest"]):
        raise ValueError("DESCRIPTOR_GRAPH_DIGEST")
    if not REPO.fullmatch(value["repository_identity"]):
        raise ValueError("DESCRIPTOR_REPOSITORY")
    if not GIT_SHA.fullmatch(value["base_sha"]):
        raise ValueError("DESCRIPTOR_BASE_SHA")
    if not UUID.fullmatch(value["epoch_id"]):
        raise ValueError("DESCRIPTOR_EPOCH_ID")
    if not WORKER.fullmatch(value["worker_id"]):
        raise ValueError("DESCRIPTOR_WORKER_ID")
    if not Path(value["worktree"]).is_absolute():
        raise ValueError("DESCRIPTOR_WORKTREE")
    return value


def empty_state(manifest_digest: str) -> dict[str, Any]:
    if not manifest_digest:
        raise ValueError("MANIFEST_DIGEST_REQUIRED")
    return {
        "schema": STATE_SCHEMA,
        "execution_manifest_digest": manifest_digest,
        "last_acknowledged_sequence": 0,
        "seen_command_ids": [],
        "results": {},
    }


def load_state(path: Path, manifest_digest: str) -> dict[str, Any]:
    if not path.exists():
        return empty_state(manifest_digest)
    value = json.loads(path.read_text())
    if value.get("schema") != STATE_SCHEMA:
        raise ValueError("STATE_SCHEMA")
    if value.get("execution_manifest_digest") != manifest_digest:
        raise ValueError("EXECUTION_MANIFEST_DRIFT")
    if not isinstance(value.get("seen_command_ids"), list) or not isinstance(value.get("results"), dict):
        raise ValueError("STATE_SHAPE")
    return value


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


# Identity fields a gall.work-result/1 may echo back. When present they must
# equal the admitted descriptor: a result for another epoch/task/subject is
# never receipted against this command.
RESULT_IDENTITY_FIELDS = ("epoch_id", "work_order_iri", "base_sha")
# A nonzero gall-work exit can never be reported as a live consequence.
LIVE_STANDINGS = frozenset({"ALIVE", "PARTIAL_ALIVE"})


def identity_digest(descriptor: dict[str, Any]) -> str:
    """Semantic identity of one admitted command (the full lease descriptor)."""
    return digest(descriptor)


def replay_mismatch(cached: dict[str, Any], identity: str) -> bool:
    """True when a cached result belongs to a different semantic identity.

    Legacy state rows written before identity binding carry no digest and are
    replayed as before; every row written now carries one.
    """
    recorded = cached.get("identity_digest") if isinstance(cached, dict) else None
    return isinstance(recorded, str) and recorded != identity


def parse_result(stdout: str) -> dict[str, Any]:
    candidates = [stdout.strip(), *reversed([line.strip() for line in stdout.splitlines() if line.strip()])]
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("schema") == RESULT_SCHEMA:
            return value
    raise ValueError("GALL_RESULT_PROTOCOL")


def run_descriptor(
    descriptor: dict[str, Any],
    *,
    state_path: Path,
    manifest_digest: str,
    zcode: str = "zcode",
    allow_do: bool = False,
    dedup_limit: int = 256,
    env: dict[str, str] | None = None,
    command_id_override: str | None = None,
) -> dict[str, Any]:
    descriptor = validate_descriptor(descriptor)
    command_id = command_id_override or digest(descriptor)
    if not isinstance(command_id, str) or not command_id.strip():
        raise ValueError("COMMAND_ID")
    try:
        state = load_state(state_path, manifest_digest)
    except ValueError as error:
        return {
            "standing": "REFUSED",
            "reason": str(error),
            "command_id": command_id,
            "executed": False,
        }

    identity = identity_digest(descriptor)
    if command_id in state["results"]:
        cached = state["results"][command_id]
        if replay_mismatch(cached, identity):
            return {
                "standing": "REFUSED",
                "reason": "REPLAY_IDENTITY_MISMATCH",
                "command_id": command_id,
                "executed": False,
            }
        return {
            "standing": "ALIVE",
            "reason": "KNOWN_REPLAY",
            "command_id": command_id,
            "executed": False,
            "result": cached["result"],
            "result_digest": cached["result_digest"],
        }

    if not allow_do:
        return {
            "standing": "REFUSED_AUTHORITY",
            "reason": "EXPLICIT_DO_ACK_REQUIRED",
            "command_id": command_id,
            "executed": False,
        }

    executable = shutil.which(zcode) if os.path.sep not in zcode else zcode
    if not executable or not Path(executable).exists():
        return {
            "standing": "BLOCKED",
            "reason": "ZCODE_UNAVAILABLE",
            "command_id": command_id,
            "executed": False,
        }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(descriptor, handle, sort_keys=True)
        handle.write("\n")
        descriptor_path = handle.name

    child_env = dict(os.environ if env is None else env)
    child_env["XAAS_WORKER"] = "1"
    child_env["XAAS_LEASE_CWD"] = descriptor["worktree"]
    child_env["XAAS_WORK_ORDER_IRI"] = descriptor["work_order_iri"]
    child_env["XAAS_EPOCH_ID"] = descriptor["epoch_id"]
    child_env["XAAS_BASE_SHA"] = descriptor["base_sha"]

    try:
        proc = subprocess.run(
            [executable, "gall-work", "--lease", descriptor_path, "--json"],
            cwd=descriptor["worktree"],
            env=child_env,
            text=True,
            capture_output=True,
            shell=False,
            check=False,
        )
    except OSError as error:
        return {
            "standing": "BLOCKED",
            "reason": "ZCODE_SPAWN_FAILED",
            "detail": error.__class__.__name__,
            "command_id": command_id,
            "executed": False,
        }
    finally:
        try:
            os.unlink(descriptor_path)
        except FileNotFoundError:
            pass

    try:
        result = parse_result(proc.stdout)
    except ValueError:
        return {
            "standing": "BUILD_BROKEN",
            "reason": "GALL_RESULT_PROTOCOL",
            "command_id": command_id,
            "executed": True,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-4096:],
            "stderr_tail": proc.stderr[-4096:],
        }

    mismatched = [
        field
        for field in RESULT_IDENTITY_FIELDS
        if field in result and result[field] != descriptor[field]
    ]
    if mismatched:
        return {
            "standing": "BUILD_BROKEN",
            "reason": "GALL_RESULT_SUBJECT_MISMATCH",
            "detail": mismatched,
            "command_id": command_id,
            "executed": True,
            "exit_code": proc.returncode,
            "result": result,
        }

    if proc.returncode != 0:
        standing = result.get("standing", "BLOCKED")
        if standing in LIVE_STANDINGS:
            return {
                "standing": "BUILD_BROKEN",
                "reason": "GALL_RESULT_EXIT_CONTRADICTION",
                "command_id": command_id,
                "executed": True,
                "exit_code": proc.returncode,
                "result": result,
            }
        return {
            "standing": standing,
            "reason": result.get("code", "GALL_WORK_NONZERO"),
            "command_id": command_id,
            "executed": True,
            "exit_code": proc.returncode,
            "result": result,
        }

    result_digest = digest(result)
    state["last_acknowledged_sequence"] = int(state.get("last_acknowledged_sequence", 0)) + 1
    state["seen_command_ids"] = [command_id] + [
        item for item in state["seen_command_ids"] if item != command_id
    ]
    state["seen_command_ids"] = state["seen_command_ids"][: max(1, dedup_limit)]
    state["results"][command_id] = {
        "result_digest": result_digest,
        "result": result,
        "identity_digest": identity,
    }

    allowed = set(state["seen_command_ids"])
    state["results"] = {key: value for key, value in state["results"].items() if key in allowed}
    save_state(state_path, state)

    return {
        "standing": result.get("standing", "PARTIAL_ALIVE"),
        "reason": "EXECUTED_RECEIPTED",
        "command_id": command_id,
        "executed": True,
        "exit_code": 0,
        "result": result,
        "result_digest": result_digest,
    }


def _refused(reason: str, command_id: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "standing": "REFUSED",
        "reason": reason,
        "executed": False,
    }
    if command_id:
        row["command_id"] = command_id
    return row


def validate_envelope(
    value: Any,
    *,
    manifest_digest: str,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("ENVELOPE_SHAPE")
    if value.get("schema", ENVELOPE_SCHEMA) != ENVELOPE_SCHEMA:
        raise ValueError("ENVELOPE_SCHEMA")

    required_strings = (
        "command_id",
        "epoch_id",
        "task_id",
        "intent_digest",
        "exact_subject",
        "verb",
        "execution_manifest_digest",
        "channel",
    )
    for field in required_strings:
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f"ENVELOPE_FIELD:{field}")

    sequence = value.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("INVALID_SEQUENCE")
    if value["channel"] not in {"control", "observe"}:
        raise ValueError("INVALID_CHANNEL")
    if value["execution_manifest_digest"] != manifest_digest:
        raise ValueError("EXECUTION_MANIFEST_DRIFT")

    current = int(time.time() * 1000) if now_ms is None else now_ms
    expires_at = value.get("expires_at")
    if expires_at is not None:
        if not isinstance(expires_at, int) or isinstance(expires_at, bool) or expires_at < current:
            raise ValueError("COMMAND_EXPIRED")

    if value["verb"] == "actuate":
        authority_ref = value.get("authority_ref")
        if value["channel"] != "control" or not isinstance(authority_ref, str) or not authority_ref.strip():
            raise ValueError("AUTHORITY_REF_REQUIRED")

    payload = validate_descriptor(value.get("payload"))
    expected_intent = payload["graph_digest"]
    expected_subject = f"{payload['repository_identity']}@{payload['base_sha']}"

    if value["intent_digest"] != expected_intent:
        raise ValueError("INTENT_DIGEST_MISMATCH")
    if value["exact_subject"] != expected_subject:
        raise ValueError("EXACT_SUBJECT_MISMATCH")
    if value["epoch_id"] != payload["epoch_id"]:
        raise ValueError("EPOCH_MISMATCH")
    if value["task_id"] != payload["work_order_iri"]:
        raise ValueError("TASK_MISMATCH")

    return value


def run_envelope(
    envelope: dict[str, Any],
    *,
    state_path: Path,
    manifest_digest: str,
    zcode: str = "zcode",
    allow_do: bool = False,
    dedup_limit: int = 256,
    env: dict[str, str] | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    command_id = envelope.get("command_id") if isinstance(envelope, dict) else None
    try:
        envelope = validate_envelope(envelope, manifest_digest=manifest_digest, now_ms=now_ms)
        state = load_state(state_path, manifest_digest)
    except ValueError as error:
        return _refused(str(error), command_id if isinstance(command_id, str) else None)

    command_id = envelope["command_id"]
    sequence = envelope["sequence"]

    if command_id in state["results"]:
        cached = state["results"][command_id]
        if replay_mismatch(cached, identity_digest(envelope["payload"])):
            return _refused("REPLAY_IDENTITY_MISMATCH", command_id)
        return {
            "standing": "ALIVE",
            "reason": "KNOWN_REPLAY",
            "command_id": command_id,
            "executed": False,
            "result": cached["result"],
            "result_digest": cached["result_digest"],
        }

    if command_id in state["seen_command_ids"] or sequence <= int(state.get("last_acknowledged_sequence", 0)):
        return {
            "standing": "ALIVE",
            "reason": "KNOWN_REPLAY",
            "command_id": command_id,
            "executed": False,
        }

    expected_sequence = int(state.get("last_acknowledged_sequence", 0)) + 1
    if sequence != expected_sequence:
        return _refused("SEQUENCE_GAP", command_id)

    row = run_descriptor(
        envelope["payload"],
        state_path=state_path,
        manifest_digest=manifest_digest,
        zcode=zcode,
        allow_do=allow_do,
        dedup_limit=dedup_limit,
        env=env,
        command_id_override=command_id,
    )
    row["sequence"] = sequence
    row["authority_ref"] = envelope.get("authority_ref")
    return row


def envelope_stream(
    lines: Iterable[str],
    *,
    manifest_digest: str,
) -> Iterable[dict[str, Any]]:
    for line in lines:
        if not line.strip():
            continue
        yield validate_envelope(json.loads(line), manifest_digest=manifest_digest)


def descriptor_stream(lines: Iterable[str]) -> Iterable[dict[str, Any]]:
    for line in lines:
        if not line.strip():
            continue
        yield validate_descriptor(json.loads(line))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--descriptor", type=Path)
    mode.add_argument("--stream", action="store_true", help="read one gall.work-lease/1 JSON document per stdin line")
    mode.add_argument("--envelope", type=Path, help="read one xaas.remote-relay-envelope/1 JSON document")
    mode.add_argument("--envelope-stream", action="store_true", help="read one relay envelope per stdin line")
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--manifest-digest", required=True)
    p.add_argument("--zcode", default="zcode")
    p.add_argument("--allow-do", action="store_true")
    p.add_argument("--dedup-limit", type=int, default=256)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        exit_status = 0
        if args.envelope or args.envelope_stream:
            envelopes = (
                envelope_stream(sys.stdin, manifest_digest=args.manifest_digest)
                if args.envelope_stream
                else [json.loads(args.envelope.read_text())]
            )
            rows = (
                run_envelope(
                    envelope,
                    state_path=args.state,
                    manifest_digest=args.manifest_digest,
                    zcode=args.zcode,
                    allow_do=args.allow_do,
                    dedup_limit=args.dedup_limit,
                )
                for envelope in envelopes
            )
        else:
            descriptors = (
                descriptor_stream(sys.stdin)
                if args.stream
                else [validate_descriptor(json.loads(args.descriptor.read_text()))]
            )
            rows = (
                run_descriptor(
                    descriptor,
                    state_path=args.state,
                    manifest_digest=args.manifest_digest,
                    zcode=args.zcode,
                    allow_do=args.allow_do,
                    dedup_limit=args.dedup_limit,
                )
                for descriptor in descriptors
            )

        for row in rows:
            print(json.dumps(row, sort_keys=True))
            if row["standing"].startswith("REFUSED"):
                exit_status = max(exit_status, 77)
            elif row["standing"] in {"BLOCKED", "BUILD_BROKEN"}:
                exit_status = max(exit_status, 69)
        return exit_status
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"standing": "BUILD_BROKEN", "reason": str(error)}, sort_keys=True))
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
