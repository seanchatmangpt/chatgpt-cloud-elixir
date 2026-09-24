"""Tests for the local-control request CLI (scripts/local_control_request.py).

Stdlib unittest only; compatible with Python 3.9 and 3.12. Exit-code contract:
0 ALIVE, 2 client refusal, 3 REFUSED, 4 BUILD_BROKEN, 5 timeout, 6 unusable
receipt. Envelope bytes must be canonical, request_id must equal the file
stem, and filed envelopes must structurally satisfy
local-control/request.schema.json (checked here with an independent minimal
validator, no jsonschema dependency).
"""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "local_control_request.py"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "local-control" / "request.schema.json"
SPEC = importlib.util.spec_from_file_location("local_control_request", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def minimal_schema_violations(value, schema, path="$"):
    """Independent minimal structural check: required/properties/type +
    additionalProperties. Deliberately separate from the CLI's validator."""
    violations = []
    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(value, dict):
        return [f"{path}: not an object"]
    if expected_type == "string" and not isinstance(value, str):
        return [f"{path}: not a string"]
    if not isinstance(value, dict):
        return violations
    for required in schema.get("required", []):
        if required not in value:
            violations.append(f"{path}: missing required {required!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        for key in value:
            if key not in properties:
                violations.append(f"{path}: additional property {key!r}")
    for key, sub_schema in properties.items():
        if key in value:
            violations.extend(minimal_schema_violations(value[key], sub_schema, f"{path}.{key}"))
    return violations


class FileCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.requests_dir = Path(self.tmp.name) / "req"

    def file_request(self, *extra_args):
        return run_cli(
            "file",
            "--requests-dir",
            str(self.requests_dir),
            "--operation",
            "system.snapshot",
            *extra_args,
        )

    def test_roundtrip_request_id_equals_stem(self):
        proc = self.file_request("--machine-star")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        path_text = proc.stdout.strip()
        self.assertTrue(path_text, "file must print the request path")
        path = Path(path_text)
        self.assertTrue(path.exists())
        # CLI prints abspath (no symlink resolution); compare resolved forms
        self.assertEqual(path.parent.resolve(), self.requests_dir.resolve())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["request_id"], path.stem)
        self.assertEqual(data["operation"], "system.snapshot")
        self.assertEqual(data["machine"], {"id": "*"})
        self.assertEqual(data["payload"], {})

    def test_generated_request_id_shape(self):
        proc = self.file_request("--machine-star")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        request_id = Path(proc.stdout.strip()).stem
        pattern = r"^system\.snapshot\.\d{8}T\d{6}Z\.[0-9a-f]{4}$"
        self.assertTrue(re.fullmatch(pattern, request_id), request_id)

    def test_canonical_bytes_stable(self):
        proc = self.file_request("--machine-star")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        raw = Path(proc.stdout.strip()).read_bytes()
        data = json.loads(raw.decode("utf-8"))
        expected = (json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        self.assertEqual(raw, expected)
        # same dict -> same bytes (deterministic canonical form)
        self.assertEqual(mod.canonical_bytes(data), raw)

    def test_expires_minutes_is_timezone_aware_utc(self):
        proc = self.file_request("--machine-star", "--expires-minutes", "10")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(Path(proc.stdout.strip()).read_text(encoding="utf-8"))
        self.assertIn("+00:00", data["expires_at"])
        parsed = datetime.fromisoformat(data["expires_at"])
        self.assertIsNotNone(parsed.tzinfo)
        delta = parsed - datetime.now(timezone.utc)
        self.assertGreaterEqual(delta, timedelta(minutes=9))
        self.assertLessEqual(delta, timedelta(minutes=11))

    def test_no_expires_key_when_unset(self):
        proc = self.file_request("--machine-star")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(Path(proc.stdout.strip()).read_text(encoding="utf-8"))
        self.assertNotIn("expires_at", data)

    def test_machine_id_flag(self):
        proc = self.file_request("--machine", "laptop-7")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(Path(proc.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(data["machine"], {"id": "laptop-7"})

    def test_payload_json_roundtrip(self):
        proc = self.file_request(
            "--machine-star",
            "--payload-json",
            '{"path":"~/repo","max_bytes":100}',
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(Path(proc.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(data["payload"], {"path": "~/repo", "max_bytes": 100})

    def test_unsafe_operation_names_refused(self):
        for bad_operation in ["../evil", "has space", "a..b", ".hidden", "trailing.", "/abs", "slash/x", ""]:
            proc = run_cli(
                "file",
                "--requests-dir",
                str(self.requests_dir),
                "--operation",
                bad_operation,
                "--machine-star",
            )
            with self.subTest(operation=bad_operation):
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("UNSAFE_OPERATION_NAME", proc.stderr)
                self.assertEqual(proc.stdout.strip(), "")
        # nothing may have been written
        self.assertFalse(self.requests_dir.exists() and any(self.requests_dir.iterdir()))

    def test_operation_outside_schema_enum_refused(self):
        proc = run_cli(
            "file",
            "--requests-dir",
            str(self.requests_dir),
            "--operation",
            "filesystem.typo",
            "--machine-star",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("SCHEMA_VIOLATION", proc.stderr)
        self.assertIn("enum", proc.stderr)

    def test_conflicting_machine_options_refused(self):
        proc = self.file_request("--machine", "laptop-7", "--machine-star")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CONFLICTING_MACHINE_OPTIONS", proc.stderr)

    def test_invalid_payload_json_refused(self):
        proc = self.file_request("--machine-star", "--payload-json", "not json")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("INVALID_PAYLOAD_JSON", proc.stderr)
        proc = self.file_request("--machine-star", "--payload-json", "[1,2]")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("INVALID_PAYLOAD_JSON", proc.stderr)

    def test_invalid_expires_minutes_refused(self):
        for bad in ["0", "-5"]:
            proc = self.file_request("--machine-star", "--expires-minutes", bad)
            with self.subTest(expires_minutes=bad):
                self.assertEqual(proc.returncode, 2)
                self.assertIn("INVALID_EXPIRES_MINUTES", proc.stderr)

    def test_filed_envelope_satisfies_request_schema(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        proc = self.file_request("--machine-star", "--expires-minutes", "10")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        envelope = json.loads(Path(proc.stdout.strip()).read_text(encoding="utf-8"))
        self.assertEqual(minimal_schema_violations(envelope, schema), [])
        # independent pattern/length check on request_id
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9._:-]+", envelope["request_id"]))
        self.assertLessEqual(len(envelope["request_id"]), 200)
        # negative control: the validator must reject a missing required field
        broken = {k: v for k, v in envelope.items() if k != "payload"}
        self.assertTrue(minimal_schema_violations(broken, schema))

    def test_request_file_exists_refused(self):
        first = self.file_request("--machine-star", "--request-id", "system.snapshot.20260923T000000Z.beef")
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.file_request("--machine-star", "--request-id", "system.snapshot.20260923T000000Z.beef")
        self.assertEqual(second.returncode, 2)
        self.assertIn("REQUEST_FILE_EXISTS", second.stderr)

    def test_unsafe_request_id_override_refused(self):
        proc = self.file_request("--machine-star", "--request-id", "../escape")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("UNSAFE_REQUEST_ID", proc.stderr)


class ListCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.requests_dir = Path(self.tmp.name) / "req"

    def _file(self, operation, request_id):
        proc = run_cli(
            "file",
            "--requests-dir",
            str(self.requests_dir),
            "--operation",
            operation,
            "--machine-star",
            "--expires-minutes",
            "5",
            "--request-id",
            request_id,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return Path(proc.stdout.strip()).stem

    def test_list_reports_receipted_and_missing(self):
        receipted_id = self._file("system.snapshot", "system.snapshot.20260923T000001Z.0001")
        missing_id = self._file("filesystem.list", "filesystem.list.20260923T000002Z.0002")
        receipts_dir = self.requests_dir.parent / "receipts"  # default sibling
        receipts_dir.mkdir(parents=True)
        (receipts_dir / f"{receipted_id}.receipt.json").write_text(
            json.dumps({"receipt_version": 1, "request_id": receipted_id, "standing": "ALIVE"}),
            encoding="utf-8",
        )
        proc = run_cli("list", "--requests-dir", str(self.requests_dir))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = {line.split()[0]: line for line in proc.stdout.strip().splitlines()}
        self.assertIn(receipted_id, lines)
        self.assertIn(missing_id, lines)
        self.assertIn("RECEIPTED", lines[receipted_id])
        self.assertIn("system.snapshot", lines[receipted_id])
        self.assertIn("machine=*", lines[receipted_id])
        self.assertIn("expires_at=", lines[receipted_id])
        self.assertIn("MISSING", lines[missing_id])
        self.assertIn("filesystem.list", lines[missing_id])

    def test_list_explicit_receipts_dir(self):
        self._file("system.snapshot", "system.snapshot.20260923T000003Z.0003")
        other_receipts = Path(self.tmp.name) / "elsewhere"
        other_receipts.mkdir()
        proc = run_cli(
            "list",
            "--requests-dir",
            str(self.requests_dir),
            "--receipts-dir",
            str(other_receipts),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MISSING", proc.stdout)


class FetchCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.receipts_dir = Path(self.tmp.name) / "receipts"
        self.receipts_dir.mkdir()
        self.request_id = "system.snapshot.20260923T000000Z.dead"

    def stage_receipt(self, standing, request_id=None):
        request_id = request_id or self.request_id
        path = self.receipts_dir / f"{request_id}.receipt.json"
        path.write_text(
            json.dumps(
                {
                    "receipt_version": 1,
                    "request_id": request_id,
                    "request_sha256": "a" * 64,
                    "standing": standing,
                }
            ),
            encoding="utf-8",
        )
        return path

    def fetch(self, *extra_args):
        return run_cli(
            "fetch",
            "--request-id",
            self.request_id,
            "--receipts-dir",
            str(self.receipts_dir),
            *extra_args,
        )

    def test_fetch_alive_exits_zero(self):
        self.stage_receipt("ALIVE")
        proc = self.fetch()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertEqual(receipt["request_id"], self.request_id)

    def test_fetch_refused_exits_three(self):
        self.stage_receipt("REFUSED")
        self.assertEqual(self.fetch().returncode, 3)

    def test_fetch_build_broken_exits_four(self):
        self.stage_receipt("BUILD_BROKEN")
        self.assertEqual(self.fetch().returncode, 4)

    def test_fetch_unknown_standing_exits_six(self):
        self.stage_receipt("MYSTERY")
        proc = self.fetch()
        self.assertEqual(proc.returncode, 6)
        self.assertIn("UNKNOWN_RECEIPT_STANDING", proc.stderr)

    def test_fetch_timeout_exits_five(self):
        proc = self.fetch("--wait-seconds", "0.2", "--poll-seconds", "0.05")
        self.assertEqual(proc.returncode, 5)
        self.assertIn("RECEIPT_TIMEOUT", proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_fetch_polls_until_receipt_appears(self):
        timer = threading.Timer(
            0.3,
            lambda: self.stage_receipt("ALIVE"),
        )
        timer.start()
        self.addCleanup(timer.cancel)
        started = time.monotonic()
        proc = self.fetch("--wait-seconds", "10", "--poll-seconds", "0.05")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertGreaterEqual(time.monotonic() - started, 0.25)
        self.assertEqual(json.loads(proc.stdout)["standing"], "ALIVE")

    def test_fetch_unsafe_request_id_refused(self):
        proc = run_cli(
            "fetch",
            "--request-id",
            "../../etc/passwd",
            "--receipts-dir",
            str(self.receipts_dir),
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("UNSAFE_REQUEST_ID", proc.stderr)

    def test_fetch_unparseable_receipt_exits_six(self):
        (self.receipts_dir / f"{self.request_id}.receipt.json").write_text("{oops", encoding="utf-8")
        proc = self.fetch()
        self.assertEqual(proc.returncode, 6)
        self.assertIn("INVALID_RECEIPT_JSON", proc.stderr)


class UnitTests(unittest.TestCase):
    def test_canonical_bytes_deterministic_and_sorted(self):
        value = {"b": 1, "a": {"z": 2, "y": 3}}
        first = mod.canonical_bytes(value)
        second = mod.canonical_bytes({"a": {"y": 3, "z": 2}, "b": 1})
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        self.assertLess(first.index(b'"a"'), first.index(b'"b"'))

    def test_validate_against_schema_flags_violations(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        good = {
            "request_id": "system.snapshot.20260923T000000Z.beef",
            "operation": "system.snapshot",
            "machine": {"id": "*"},
            "payload": {},
        }
        self.assertEqual(mod.validate_against_schema(good, schema), [])
        self.assertTrue(mod.validate_against_schema({"operation": "x"}, schema))
        extra = dict(good, sneaky=1)
        self.assertTrue(mod.validate_against_schema(extra, schema))
        bad_operation = dict(good, operation="nope.nope")
        self.assertTrue(mod.validate_against_schema(bad_operation, schema))


if __name__ == "__main__":
    unittest.main()
