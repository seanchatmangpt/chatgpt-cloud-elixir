import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "project_memory_orphan_report.py"
spec = importlib.util.spec_from_file_location("project_memory_orphan_report", SCRIPT)
orphan_report = importlib.util.module_from_spec(spec)
sys.modules["project_memory_orphan_report"] = orphan_report
assert spec.loader is not None
spec.loader.exec_module(orphan_report)


def write_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def request(request_id: str, operation: str, key: str = "some/key", extra_payload=None):
    payload = {"record": {"key": key, "title": request_id, "body": "x"}}
    if operation in ("memory.read", "memory.query"):
        payload = {"key": key}
    if extra_payload:
        payload.update(extra_payload)
    return {
        "request_id": request_id,
        "operation": operation,
        "project": {"owner": "seanchatmangpt", "number": 2},
        "payload": payload,
    }


def receipt(request_id: str, operation: str, standing: str = "ALIVE", reason=None):
    doc = {"request_id": request_id, "operation": operation, "standing": standing}
    if reason is not None:
        doc["reason"] = reason
    return doc


class LoadJsonSafeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_json_object(self):
        p = self.root / "a.json"
        write_json(p, {"a": 1})
        data, error = orphan_report.load_json_safe(p)
        self.assertIsNone(error)
        self.assertEqual(data, {"a": 1})

    def test_malformed_json_reports_error_not_raise(self):
        p = self.root / "broken.json"
        write_text(p, '{"a": 1}}')
        data, error = orphan_report.load_json_safe(p)
        self.assertIsNone(data)
        self.assertIn("JSONDecodeError", error)

    def test_top_level_non_object_is_not_an_error(self):
        # load_json_safe itself only reports parse errors; "not an object" is a
        # schema-anomaly concern handled by describe_schema_anomaly/scan, not a parse
        # failure -- a bare JSON array or string is syntactically valid JSON.
        p = self.root / "array.json"
        write_text(p, "[1, 2, 3]")
        data, error = orphan_report.load_json_safe(p)
        self.assertIsNone(error)
        self.assertEqual(data, [1, 2, 3])


class ReceiptStemTests(unittest.TestCase):
    def test_strips_receipt_json_suffix(self):
        self.assertEqual(
            orphan_report.receipt_stem(pathlib.Path("20260825T090000Z-a.receipt.json")),
            "20260825T090000Z-a",
        )

    def test_non_receipt_file_returns_none(self):
        self.assertIsNone(orphan_report.receipt_stem(pathlib.Path("20260828T033600Z-ws2-hourly-credit.json")))


class DescribeSchemaAnomalyTests(unittest.TestCase):
    def test_missing_operation_with_type_field(self):
        reason = orphan_report.describe_schema_anomaly({"type": "project2.work_claim", "version": 1})
        self.assertIn("missing 'operation' key", reason)
        self.assertIn("project2.work_claim", reason)

    def test_missing_operation_no_type_field(self):
        reason = orphan_report.describe_schema_anomaly({"foo": "bar"})
        self.assertEqual(reason, "missing 'operation' key")

    def test_non_dict_top_level(self):
        reason = orphan_report.describe_schema_anomaly([1, 2, 3])
        self.assertIn("not an object", reason)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.requests_dir = self.root / "requests"
        self.receipts_dir = self.root / "receipts"
        self.requests_dir.mkdir(parents=True)
        self.receipts_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_pair(self, request_id: str, operation: str, *, with_receipt: bool = True, standing: str = "ALIVE"):
        write_json(self.requests_dir / f"{request_id}.json", request(request_id, operation))
        if with_receipt:
            write_json(
                self.receipts_dir / f"{request_id}.receipt.json",
                receipt(request_id, operation, standing=standing),
            )

    def test_empty_dirs_produce_empty_report(self):
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.total_requests, 0)
        self.assertEqual(report.total_receipts, 0)
        self.assertEqual(report.orphan_request_count, 0)
        self.assertEqual(report.orphan_receipt_count, 0)
        self.assertEqual(report.mutating_orphan_count, 0)

    def test_matched_pair_is_not_orphaned(self):
        self.write_pair("r1", "memory.read")
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.orphan_request_count, 0)
        self.assertEqual(report.orphan_receipt_count, 0)

    def test_orphan_mutating_request_detected_and_flagged_mutating(self):
        self.write_pair("r1", "memory.upsert", with_receipt=False)
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.orphan_request_count, 1)
        self.assertEqual(report.mutating_orphan_count, 1)
        self.assertTrue(report.orphan_requests[0].mutating)
        self.assertEqual(report.orphan_requests[0].operation, "memory.upsert")

    def test_orphan_read_only_request_detected_but_not_mutating(self):
        self.write_pair("r1", "memory.read", with_receipt=False)
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.orphan_request_count, 1)
        self.assertEqual(report.mutating_orphan_count, 0)
        self.assertFalse(report.orphan_requests[0].mutating)

    def test_all_five_mutating_operations_flagged_mutating(self):
        for i, op in enumerate(
            ["memory.create", "memory.update", "memory.upsert", "memory.archive", "memory.delete"]
        ):
            self.write_pair(f"r{i}", op, with_receipt=False)
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.mutating_orphan_count, 5)

    def test_orphan_requests_by_operation_breakdown(self):
        self.write_pair("r1", "memory.upsert", with_receipt=False)
        self.write_pair("r2", "memory.upsert", with_receipt=False)
        self.write_pair("r3", "memory.read", with_receipt=False)
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.orphan_requests_by_operation, {"memory.upsert": 2, "memory.read": 1})

    def test_orphan_receipt_detected(self):
        write_json(
            self.receipts_dir / "no-request.receipt.json",
            receipt("no-request", "memory.upsert"),
        )
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.orphan_receipt_count, 1)
        self.assertEqual(report.orphan_receipts[0].stem, "no-request")

    def test_stray_receipts_dir_file_without_receipt_suffix_is_ignored(self):
        # Mirrors the real corpus's project-memory/receipts/20260828T033600Z-ws2-hourly-credit.json
        # (a completely different schema, no ".receipt.json" suffix) -- must never be
        # picked up as an orphan receipt or crash the scan.
        write_text(self.receipts_dir / "20260828T033600Z-ws2-hourly-credit.json", '{"type": "other"}')
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.total_receipts, 0)
        self.assertEqual(report.orphan_receipt_count, 0)

    def test_nested_request_subdirectory_is_scanned_and_matches_flat_receipt(self):
        # Mirrors the real corpus's project-memory/requests/2026-08-25/ subdirectory --
        # requests can be nested one level deep while receipts stay flat.
        write_json(
            self.requests_dir / "2026-08-25" / "nested-read.json",
            request("nested-read", "memory.read"),
        )
        write_json(
            self.receipts_dir / "nested-read.receipt.json",
            receipt("nested-read", "memory.read"),
        )
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.total_requests, 1)
        self.assertEqual(report.orphan_request_count, 0)
        self.assertEqual(report.orphan_receipt_count, 0)

    def test_nested_request_without_receipt_is_a_real_orphan_not_missed(self):
        write_json(
            self.requests_dir / "2026-08-25" / "nested-orphan.json",
            request("nested-orphan", "memory.upsert"),
        )
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(report.orphan_request_count, 1)
        self.assertEqual(report.mutating_orphan_count, 1)

    def test_parse_failure_reports_error_and_excludes_from_schema_anomalies(self):
        write_text(self.requests_dir / "broken.json", '{"operation": "memory.read"}}')
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(report.parse_failures), 1)
        self.assertIn("JSONDecodeError", report.parse_failures[0].error)
        self.assertEqual(len(report.schema_anomalies), 0)
        # An unparseable request also can't be matched, so it counts as orphaned too --
        # mirrors the real corpus's 13 corrupted files, all also missing a real receipt
        # match at the exact stem (their receipts DO exist and are correctly BUILD_BROKEN,
        # but this assertion is about the request side accounting, not a receipt lookup).
        self.assertEqual(report.orphan_request_count, 1)
        self.assertFalse(report.orphan_requests[0].mutating)  # operation unknown -> not mutating

    def test_schema_anomaly_with_matching_receipt_is_not_an_orphan(self):
        # Mirrors the real corpus's 2 "project2.work_claim" files: valid JSON, wrong
        # envelope shape, but DOES have a matching (REFUSED) receipt.
        write_json(
            self.requests_dir / "claim1.json",
            {"type": "project2.work_claim", "version": 1, "status": "TERMINAL"},
        )
        write_json(
            self.receipts_dir / "claim1.receipt.json",
            {"standing": "REFUSED", "reason": "INVALID_REQUEST", "request_id": None},
        )
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(report.schema_anomalies), 1)
        self.assertIn("project2.work_claim", report.schema_anomalies[0].reason)
        self.assertEqual(report.orphan_request_count, 0)

    def test_schema_anomaly_without_matching_receipt_is_both(self):
        write_json(self.requests_dir / "claim2.json", {"type": "project2.work_claim"})
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(report.schema_anomalies), 1)
        self.assertEqual(report.orphan_request_count, 1)

    def test_build_broken_receipt_detected(self):
        self.write_pair("r1", "memory.upsert", standing="BUILD_BROKEN")
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(report.build_broken_receipts), 1)
        self.assertEqual(report.build_broken_receipts[0].stem, "r1")

    def test_alive_and_refused_receipts_not_flagged_build_broken(self):
        self.write_pair("r1", "memory.upsert", standing="ALIVE")
        self.write_pair("r2", "memory.read", standing="REFUSED")
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(report.build_broken_receipts), 0)

    def test_receipt_parse_failure_does_not_crash_scan_and_is_reported(self):
        write_json(self.requests_dir / "r1.json", request("r1", "memory.read"))
        write_text(self.receipts_dir / "r1.receipt.json", '{"standing": "ALIVE"}}')
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(report.receipt_parse_failures), 1)
        # a receipt that fails to parse still counts as "present" for matching purposes
        # (its filename stem is known even though its content isn't) -- so the request
        # is not reported as orphaned, and the receipt itself is not double counted as
        # both build_broken and a parse failure.
        self.assertEqual(report.orphan_request_count, 0)
        self.assertEqual(len(report.build_broken_receipts), 0)

    def test_real_corpus_reproduction_shape(self):
        # A miniature version of the real project-memory/ corpus's exact shape (see the
        # docstring's "recursion note"): one pointer-style write with a stale duplicate
        # (both fine), one corrupted trailing-brace request whose receipt correctly
        # recorded BUILD_BROKEN, one work-claim schema anomaly with a REFUSED receipt,
        # one genuinely orphaned memory.upsert, and one nested-subdirectory request
        # whose receipt lives flat.
        self.write_pair("20260825T090000Z-ledger-a", "memory.upsert")
        write_text(
            self.requests_dir / "20260825T083000Z-corrupt.json",
            json.dumps(request("20260825T083000Z-corrupt", "memory.upsert")) + "}",
        )
        write_json(
            self.receipts_dir / "20260825T083000Z-corrupt.receipt.json",
            {"standing": "BUILD_BROKEN", "reason": "UNHANDLED_PROXY_FAILURE"},
        )
        write_json(self.requests_dir / "20260828T031900Z-claim.json", {"type": "project2.work_claim"})
        write_json(
            self.receipts_dir / "20260828T031900Z-claim.receipt.json",
            {"standing": "REFUSED", "reason": "INVALID_REQUEST"},
        )
        self.write_pair("20260828T100000Z-orphan-upsert", "memory.upsert", with_receipt=False)
        write_json(
            self.requests_dir / "2026-08-25" / "20260825T110000Z-nested-read.json",
            request("20260825T110000Z-nested-read", "memory.read"),
        )
        write_json(
            self.receipts_dir / "20260825T110000Z-nested-read.receipt.json",
            receipt("20260825T110000Z-nested-read", "memory.read"),
        )

        report = orphan_report.scan(self.requests_dir, self.receipts_dir)

        self.assertEqual(report.total_requests, 5)
        self.assertEqual(report.total_receipts, 4)
        self.assertEqual(len(report.parse_failures), 1)
        self.assertEqual(len(report.schema_anomalies), 1)
        self.assertEqual(len(report.build_broken_receipts), 1)
        self.assertEqual(report.orphan_request_count, 1)  # only the un-receipted upsert
        self.assertEqual(report.mutating_orphan_count, 1)
        self.assertEqual(report.orphan_receipt_count, 0)


class ReportOutputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.requests_dir = self.root / "requests"
        self.receipts_dir = self.root / "receipts"
        self.requests_dir.mkdir(parents=True)
        self.receipts_dir.mkdir(parents=True)
        write_json(self.requests_dir / "orphan.json", request("orphan", "memory.upsert"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_to_dict_roundtrips_through_json(self):
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        payload = report.to_dict()
        json.dumps(payload)  # must not raise
        self.assertEqual(payload["orphan_requests"]["count"], 1)
        self.assertEqual(payload["orphan_requests"]["mutating_count"], 1)
        self.assertEqual(payload["orphan_requests"]["by_operation"], {"memory.upsert": 1})

    def test_human_report_contains_key_numbers(self):
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        text = orphan_report.format_human_report(report, mutating_orphan_threshold=0)
        self.assertIn("requests with no matching receipt: 1 (1 mutating, 0 read-only)", text)
        self.assertIn("FAIL:", text)

    def test_human_report_ok_when_under_threshold(self):
        report = orphan_report.scan(self.requests_dir, self.receipts_dir)
        text = orphan_report.format_human_report(report, mutating_orphan_threshold=5)
        self.assertIn("OK:", text)
        self.assertNotIn("FAIL:", text)


class RejectOutputInsideProjectMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "project-memory").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_path_under_project_memory_rejected(self):
        target = self.root / "project-memory" / "report.json"
        error = orphan_report._reject_output_inside_project_memory(target, self.root)
        self.assertIsNotNone(error)
        self.assertIn("read-only", error)

    def test_path_under_project_memory_requests_rejected(self):
        (self.root / "project-memory" / "requests").mkdir(parents=True)
        target = self.root / "project-memory" / "requests" / "sneaky.json"
        error = orphan_report._reject_output_inside_project_memory(target, self.root)
        self.assertIsNotNone(error)

    def test_path_outside_project_memory_accepted(self):
        target = self.root / "reports" / "orphan.json"
        error = orphan_report._reject_output_inside_project_memory(target, self.root)
        self.assertIsNone(error)

    def test_sibling_directory_with_similar_prefix_not_confused(self):
        # "project-memory-backup" must not be treated as inside "project-memory" by a
        # naive string-prefix check.
        target = self.root / "project-memory-backup" / "orphan.json"
        error = orphan_report._reject_output_inside_project_memory(target, self.root)
        self.assertIsNone(error)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "project-memory" / "requests").mkdir(parents=True)
        (self.root / "project-memory" / "receipts").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_no_orphans_exits_zero(self):
        write_json(
            self.root / "project-memory" / "requests" / "r1.json",
            request("r1", "memory.read"),
        )
        write_json(
            self.root / "project-memory" / "receipts" / "r1.receipt.json",
            receipt("r1", "memory.read"),
        )
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_orphan_mutating_request_exits_nonzero(self):
        write_json(
            self.root / "project-memory" / "requests" / "r1.json",
            request("r1", "memory.upsert"),
        )
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL:", result.stdout)

    def test_threshold_flag_suppresses_failure(self):
        write_json(
            self.root / "project-memory" / "requests" / "r1.json",
            request("r1", "memory.upsert"),
        )
        result = self.run_cli("--mutating-orphan-threshold", "1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK:", result.stdout)

    def test_json_flag_produces_valid_json(self):
        write_json(
            self.root / "project-memory" / "requests" / "r1.json",
            request("r1", "memory.upsert"),
        )
        result = self.run_cli("--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["orphan_requests"]["mutating_count"], 1)
        self.assertFalse(payload["exit_ok"])

    def test_output_flag_writes_report_outside_project_memory(self):
        write_json(
            self.root / "project-memory" / "requests" / "r1.json",
            request("r1", "memory.read"),
        )
        write_json(
            self.root / "project-memory" / "receipts" / "r1.receipt.json",
            receipt("r1", "memory.read"),
        )
        out_path = self.root / "reports" / "orphan.txt"
        result = self.run_cli("--output", str(out_path))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(out_path.is_file())
        self.assertIn("requests with no matching receipt: 0", out_path.read_text(encoding="utf-8"))

    def test_output_flag_refuses_path_inside_project_memory(self):
        out_path = self.root / "project-memory" / "sneaky-report.json"
        result = self.run_cli("--output", str(out_path))
        self.assertEqual(result.returncode, 2)
        self.assertIn("read-only", result.stderr)
        self.assertFalse(out_path.exists())

    def test_missing_requests_dir_is_a_clean_error(self):
        empty_root = pathlib.Path(tempfile.mkdtemp())
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(empty_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requests directory not found", result.stderr)

    def test_cli_never_modifies_source_directories(self):
        write_json(
            self.root / "project-memory" / "requests" / "r1.json",
            request("r1", "memory.upsert"),
        )
        req_path = self.root / "project-memory" / "requests" / "r1.json"
        before = req_path.read_text(encoding="utf-8")
        before_mtime = req_path.stat().st_mtime
        self.run_cli("--json")
        self.run_cli()
        after = req_path.read_text(encoding="utf-8")
        after_mtime = req_path.stat().st_mtime
        self.assertEqual(before, after)
        self.assertEqual(before_mtime, after_mtime)
        # confirm no stray files were created anywhere under project-memory/
        all_files = sorted(p.name for p in (self.root / "project-memory").rglob("*") if p.is_file())
        self.assertEqual(all_files, ["r1.json"])


if __name__ == "__main__":
    unittest.main()
