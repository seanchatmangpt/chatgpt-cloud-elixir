import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "project_memory_bus.py"
spec = importlib.util.spec_from_file_location("project_memory_bus", SCRIPT)
bus = importlib.util.module_from_spec(spec)
sys.modules["project_memory_bus"] = bus
assert spec.loader is not None
spec.loader.exec_module(bus)


class DigestTests(unittest.TestCase):
    def test_canonical_digest_ignores_json_key_order(self):
        left = {"b": 2, "a": {"y": 2, "x": 1}}
        right = {"a": {"x": 1, "y": 2}, "b": 2}
        self.assertEqual(bus.canonical_digest(left), bus.canonical_digest(right))


class AdmissionTests(unittest.TestCase):
    def test_malformed_json_is_typed_refusal_without_project_actuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            request = root / "bad.json"
            receipt = root / "bad.receipt.json"
            request.write_text('{"request_id":"bad"}}', encoding="utf-8")

            code = bus.main(["--request", str(request), "--receipt", str(receipt)])
            self.assertEqual(2, code)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual("REFUSED", data["standing"])
            self.assertEqual("INVALID_REQUEST_JSON", data["reason"])
            self.assertFalse(data["actuation_performed"])
            self.assertTrue(data["request_transport_sha256"].startswith("sha256:"))

    def test_non_object_json_is_typed_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            request = root / "array.json"
            receipt = root / "array.receipt.json"
            request.write_text("[]", encoding="utf-8")

            code = bus.main(["--request", str(request), "--receipt", str(receipt)])
            self.assertEqual(2, code)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual("INVALID_REQUEST_ROOT", data["reason"])


class ReplayTests(unittest.TestCase):
    def test_exact_alive_receipt_short_circuits_replay_without_token(self):
        request_data = {
            "request_id": "replay-1",
            "operation": "memory.query",
            "project": {"owner": "seanchatmangpt", "number": 2},
            "payload": {"text": "frontier"},
        }
        digest = bus.canonical_digest(request_data)

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            request = root / "request.json"
            receipt = root / "receipt.json"
            request.write_text(json.dumps(request_data), encoding="utf-8")
            receipt.write_text(
                json.dumps(
                    {
                        "standing": "ALIVE",
                        "request_id": "replay-1",
                        "operation": "memory.query",
                        "request_sha256": digest,
                    }
                ),
                encoding="utf-8",
            )

            code = bus.main(["--request", str(request), "--receipt", str(receipt)])
            self.assertEqual(0, code)
            # If the gate attempted Project access, the blank test environment would fail.
            persisted = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual("ALIVE", persisted["standing"])
            self.assertEqual(digest, persisted["request_sha256"])

    def test_changed_request_does_not_reuse_alive_receipt(self):
        receipt = {
            "standing": "ALIVE",
            "request_id": "x",
            "operation": "memory.query",
            "request_sha256": "sha256:old",
        }
        self.assertFalse(
            bus.is_exact_alive_replay(
                receipt,
                request_sha256="sha256:new",
                request_id="x",
                operation="memory.query",
            )
        )


if __name__ == "__main__":
    unittest.main()
