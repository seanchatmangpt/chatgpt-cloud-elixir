import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "project_memory_prune.py"
spec = importlib.util.spec_from_file_location("project_memory_prune", SCRIPT)
prune = importlib.util.module_from_spec(spec)
sys.modules["project_memory_prune"] = prune
assert spec.loader is not None
spec.loader.exec_module(prune)


def write_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def upsert_request(request_id: str, key: str, operation: str = "memory.upsert", extra_payload=None):
    payload = {"record": {"key": key, "title": request_id, "kind": "test.kind", "body": "x"}}
    if operation == "memory.update":
        # memory.update takes key as a separate top-level payload param, per
        # scripts/project_memory_proxy.py's execute_request(); record may omit it.
        payload = {"key": key, "record": {"title": request_id, "body": "x"}}
    if extra_payload:
        payload.update(extra_payload)
    return {
        "request_id": request_id,
        "operation": operation,
        "project": {"owner": "seanchatmangpt", "number": 2},
        "payload": payload,
    }


def read_request(request_id: str, key: str):
    return {
        "request_id": request_id,
        "operation": "memory.read",
        "project": {"owner": "seanchatmangpt", "number": 2},
        "payload": {"key": key},
    }


class TimestampParsingTests(unittest.TestCase):
    def test_full_precision(self):
        result = prune.parse_filename_timestamp("20260825T092610Z-select-run-control-start.json")
        self.assertEqual(result, ("20260825092610", "2026-08"))

    def test_no_seconds(self):
        result = prune.parse_filename_timestamp("20260825T2225Z-measure-pre-snapshot.json")
        self.assertEqual(result, ("20260825222500", "2026-08"))

    def test_date_only(self):
        result = prune.parse_filename_timestamp("20260826-project-two-semantic-capability-upsert.json")
        self.assertEqual(result, ("20260826000000", "2026-08"))

    def test_no_recognizable_timestamp(self):
        self.assertIsNone(prune.parse_filename_timestamp("select-105708-run-control.json"))
        self.assertIsNone(prune.parse_filename_timestamp("cell4-ggen-ocel-20260826T193631Z-thing.json"))


class ExtractWriteKeyTests(unittest.TestCase):
    def test_upsert_key_from_record(self):
        req = upsert_request("r1", "dfcm/ledger/current", operation="memory.upsert")
        self.assertEqual(prune.extract_write_key(req), "dfcm/ledger/current")

    def test_create_key_from_record(self):
        req = upsert_request("r1", "dfcm/frontier/current", operation="memory.create")
        self.assertEqual(prune.extract_write_key(req), "dfcm/frontier/current")

    def test_update_key_from_top_level_payload(self):
        req = upsert_request("r1", "dfcm/select/latest", operation="memory.update")
        # sanity: the record itself must NOT carry the key, mirroring real corpus shape
        self.assertNotIn("key", req["payload"]["record"])
        self.assertEqual(prune.extract_write_key(req), "dfcm/select/latest")

    def test_read_operation_has_no_write_key(self):
        req = read_request("r1", "dfcm/ledger/current")
        self.assertIsNone(prune.extract_write_key(req))

    def test_query_operation_has_no_write_key(self):
        req = {
            "request_id": "r1",
            "operation": "memory.query",
            "project": {"owner": "seanchatmangpt", "number": 2},
            "payload": {"kind": "dfcm.frontier"},
        }
        self.assertIsNone(prune.extract_write_key(req))

    def test_missing_key_returns_none(self):
        req = {
            "request_id": "r1",
            "operation": "memory.upsert",
            "project": {"owner": "seanchatmangpt", "number": 2},
            "payload": {"record": {"title": "no key here"}},
        }
        self.assertIsNone(prune.extract_write_key(req))


class PointerKeyHeuristicTests(unittest.TestCase):
    def test_current_and_latest_match(self):
        self.assertTrue(prune.is_pointer_key("dfcm/ledger/current"))
        self.assertTrue(prune.is_pointer_key("dfcm/select/latest"))
        self.assertTrue(prune.is_pointer_key("dfcm/run-control/select/current"))

    def test_case_insensitive(self):
        self.assertTrue(prune.is_pointer_key("dfcm/ledger/Current"))

    def test_non_pointer_keys_do_not_match(self):
        self.assertFalse(prune.is_pointer_key("dfcm/run/measure/20260825T094630Z/abcd1234"))
        self.assertFalse(prune.is_pointer_key("plant/ws1/run_lease"))
        self.assertFalse(prune.is_pointer_key("plant/claims/ggen/foo/ws1-20260827T1900-0700"))
        # "current" appearing mid-string, not as the trailing path segment, must not match
        self.assertFalse(prune.is_pointer_key("dfcm/currently/observed"))


class BuildPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.requests_dir = self.root / "requests"
        self.receipts_dir = self.root / "receipts"
        self.requests_dir.mkdir(parents=True)
        self.receipts_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_pair(self, request_id: str, key: str, *, with_receipt: bool = True, operation: str = "memory.upsert"):
        write_json(self.requests_dir / f"{request_id}.json", upsert_request(request_id, key, operation=operation))
        if with_receipt:
            write_json(
                self.receipts_dir / f"{request_id}.receipt.json",
                {"request_id": request_id, "operation": operation, "standing": "ALIVE"},
            )

    def test_three_writes_same_pointer_key_two_candidates_one_kept_live(self):
        self.write_pair("20260825T090000Z-a", "dfcm/ledger/current")
        self.write_pair("20260825T100000Z-b", "dfcm/ledger/current")
        self.write_pair("20260825T110000Z-c", "dfcm/ledger/current")

        plan = prune.build_plan(self.requests_dir, self.receipts_dir)

        self.assertEqual(plan.count, 2)
        candidate_names = {c.request_path.name for c in plan.candidates}
        self.assertEqual(candidate_names, {"20260825T090000Z-a.json", "20260825T100000Z-b.json"})
        self.assertEqual(plan.kept_live["dfcm/ledger/current"].name, "20260825T110000Z-c.json")

    def test_single_write_never_a_candidate(self):
        self.write_pair("20260825T090000Z-only", "dfcm/frontier/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan.count, 0)
        self.assertEqual(plan.kept_live["dfcm/frontier/current"].name, "20260825T090000Z-only.json")

    def test_non_pointer_key_never_grouped_even_with_multiple_writes(self):
        self.write_pair("20260825T090000Z-run1", "dfcm/run/measure/20260825T090000Z/deadbeef")
        self.write_pair("20260825T100000Z-run2", "dfcm/run/measure/20260825T100000Z/cafebabe")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan.count, 0)
        self.assertEqual(plan.kept_live, {})

    def test_read_only_requests_never_candidates(self):
        write_json(
            self.requests_dir / "20260825T090000Z-read.json",
            read_request("20260825T090000Z-read", "dfcm/ledger/current"),
        )
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan.count, 0)
        self.assertEqual(plan.kept_live, {})

    def test_candidate_without_matching_receipt_still_included(self):
        self.write_pair("20260825T090000Z-noreceipt", "dfcm/select/latest", with_receipt=False)
        self.write_pair("20260825T100000Z-newer", "dfcm/select/latest")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan.count, 1)
        self.assertIsNone(plan.candidates[0].receipt_path)

    def test_malformed_json_is_skipped_not_raised(self):
        (self.requests_dir / "20260825T090000Z-broken.json").write_text('{"a": 1}}', encoding="utf-8")
        self.write_pair("20260825T100000Z-ok", "dfcm/ledger/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(plan.skipped_unparseable), 1)
        self.assertEqual(plan.skipped_unparseable[0].path.name, "20260825T090000Z-broken.json")
        # the well-formed request is unaffected and (being the only real write) stays live
        self.assertEqual(plan.count, 0)

    def test_no_timestamp_filename_is_skipped_not_guessed(self):
        write_json(self.requests_dir / "select-run-control.json", upsert_request("select-run-control", "dfcm/ledger/current"))
        self.write_pair("20260825T100000Z-ok", "dfcm/ledger/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(len(plan.skipped_no_timestamp), 1)
        self.assertEqual(plan.skipped_no_timestamp[0].name, "select-run-control.json")
        # only one dateable write to this key exists, so it alone is kept live; nothing archived
        self.assertEqual(plan.count, 0)

    def test_update_operation_grouped_by_top_level_payload_key(self):
        self.write_pair("20260825T090000Z-u1", "dfcm/select/latest", operation="memory.update")
        self.write_pair("20260825T100000Z-u2", "dfcm/select/latest", operation="memory.update")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan.count, 1)
        self.assertEqual(plan.candidates[0].request_path.name, "20260825T090000Z-u1.json")


class ApplyPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.requests_dir = self.root / "requests"
        self.receipts_dir = self.root / "receipts"
        self.archive_dir = self.root / "archive"
        self.requests_dir.mkdir(parents=True)
        self.receipts_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_pair(self, request_id: str, key: str, *, with_receipt: bool = True):
        write_json(self.requests_dir / f"{request_id}.json", upsert_request(request_id, key))
        if with_receipt:
            write_json(
                self.receipts_dir / f"{request_id}.receipt.json",
                {"request_id": request_id, "operation": "memory.upsert", "standing": "ALIVE"},
            )

    def test_dry_run_makes_zero_filesystem_changes(self):
        self.write_pair("20260825T090000Z-a", "dfcm/ledger/current")
        self.write_pair("20260825T100000Z-b", "dfcm/ledger/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan.count, 1)

        # No apply_plan call at all: this is the dry-run path exercised by main()
        # without --apply. Confirm nothing moved and archive dir was never created.
        self.assertFalse(self.archive_dir.exists())
        self.assertTrue((self.requests_dir / "20260825T090000Z-a.json").exists())
        self.assertTrue((self.receipts_dir / "20260825T090000Z-a.receipt.json").exists())

    def test_apply_moves_superseded_pair_preserves_filenames(self):
        self.write_pair("20260825T090000Z-a", "dfcm/ledger/current")
        self.write_pair("20260825T100000Z-b", "dfcm/ledger/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)

        moved = prune.apply_plan(plan, self.archive_dir)

        self.assertEqual(len(moved), 2)  # request + receipt for the superseded "a"
        archived_request = self.archive_dir / "2026-08" / "requests" / "20260825T090000Z-a.json"
        archived_receipt = self.archive_dir / "2026-08" / "receipts" / "20260825T090000Z-a.receipt.json"
        self.assertTrue(archived_request.is_file())
        self.assertTrue(archived_receipt.is_file())
        # original locations are now empty for the archived pair
        self.assertFalse((self.requests_dir / "20260825T090000Z-a.json").exists())
        self.assertFalse((self.receipts_dir / "20260825T090000Z-a.receipt.json").exists())

    def test_apply_never_touches_most_recent_pair(self):
        self.write_pair("20260825T090000Z-a", "dfcm/ledger/current")
        self.write_pair("20260825T100000Z-b", "dfcm/ledger/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        prune.apply_plan(plan, self.archive_dir)

        self.assertTrue((self.requests_dir / "20260825T100000Z-b.json").is_file())
        self.assertTrue((self.receipts_dir / "20260825T100000Z-b.receipt.json").is_file())
        self.assertFalse((self.archive_dir / "2026-08" / "requests" / "20260825T100000Z-b.json").exists())

    def test_apply_moves_request_only_when_receipt_missing(self):
        self.write_pair("20260825T090000Z-noreceipt", "dfcm/select/latest", with_receipt=False)
        self.write_pair("20260825T100000Z-newer", "dfcm/select/latest")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        moved = prune.apply_plan(plan, self.archive_dir)

        self.assertEqual(len(moved), 1)
        self.assertTrue((self.archive_dir / "2026-08" / "requests" / "20260825T090000Z-noreceipt.json").is_file())
        self.assertFalse((self.archive_dir / "2026-08" / "receipts").exists())

    def test_apply_is_idempotent_across_two_runs(self):
        self.write_pair("20260825T090000Z-a", "dfcm/ledger/current")
        self.write_pair("20260825T100000Z-b", "dfcm/ledger/current")
        plan1 = prune.build_plan(self.requests_dir, self.receipts_dir)
        first_moved = prune.apply_plan(plan1, self.archive_dir)
        self.assertEqual(len(first_moved), 2)

        # Re-scanning after the first apply: the archived pair is gone from the live
        # dirs, so it is no longer even discovered as a candidate; only the live
        # pointer remains, and it alone is never a candidate for its own key.
        plan2 = prune.build_plan(self.requests_dir, self.receipts_dir)
        self.assertEqual(plan2.count, 0)
        second_moved = prune.apply_plan(plan2, self.archive_dir)
        self.assertEqual(second_moved, [])

        # nothing was duplicated or clobbered
        archived_request = self.archive_dir / "2026-08" / "requests" / "20260825T090000Z-a.json"
        self.assertTrue(archived_request.is_file())

    def test_never_deletes_only_moves(self):
        self.write_pair("20260825T090000Z-a", "dfcm/ledger/current")
        self.write_pair("20260825T100000Z-b", "dfcm/ledger/current")
        plan = prune.build_plan(self.requests_dir, self.receipts_dir)
        prune.apply_plan(plan, self.archive_dir)

        # total file count is conserved (moved, not deleted): 2 requests + 2 receipts
        # before, same 4 files after, just relocated.
        all_files_after = list(self.root.rglob("*.json"))
        self.assertEqual(len(all_files_after), 4)


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

    def test_dry_run_json_output_and_no_apply_flag(self):
        write_json(
            self.root / "project-memory" / "requests" / "20260825T090000Z-a.json",
            upsert_request("20260825T090000Z-a", "dfcm/ledger/current"),
        )
        write_json(
            self.root / "project-memory" / "requests" / "20260825T100000Z-b.json",
            upsert_request("20260825T100000Z-b", "dfcm/ledger/current"),
        )

        result = self.run_cli("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["candidate_count"], 1)
        self.assertFalse(report["applied"])
        self.assertFalse((self.root / "project-memory" / "archive").exists())

    def test_apply_flag_actually_moves_files(self):
        write_json(
            self.root / "project-memory" / "requests" / "20260825T090000Z-a.json",
            upsert_request("20260825T090000Z-a", "dfcm/ledger/current"),
        )
        write_json(
            self.root / "project-memory" / "requests" / "20260825T100000Z-b.json",
            upsert_request("20260825T100000Z-b", "dfcm/ledger/current"),
        )

        result = self.run_cli("--apply", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["applied"])
        self.assertEqual(len(report["moved"]), 1)
        archived = self.root / "project-memory" / "archive" / "2026-08" / "requests" / "20260825T090000Z-a.json"
        self.assertTrue(archived.is_file())

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


if __name__ == "__main__":
    unittest.main()
