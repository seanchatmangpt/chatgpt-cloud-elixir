import importlib.util
import pathlib
import sys
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "project_memory_proxy.py"
spec = importlib.util.spec_from_file_location("project_memory_proxy", SCRIPT)
proxy = importlib.util.module_from_spec(spec)
sys.modules["project_memory_proxy"] = proxy
assert spec.loader is not None
spec.loader.exec_module(proxy)


class MemoryEncodingTests(unittest.TestCase):
    def test_round_trip(self):
        meta = {"key": "dfcm/frontier/current", "kind": "dfcm.frontier", "tags": ["a", "b"]}
        rendered = proxy.encode_memory_body(meta, "hello\nworld")
        decoded, body = proxy.decode_memory_body(rendered)
        self.assertEqual(meta, decoded)
        self.assertEqual("hello\nworld", body)

    def test_plain_body_is_not_memory(self):
        meta, body = proxy.decode_memory_body("plain")
        self.assertIsNone(meta)
        self.assertEqual("plain", body)


class ValidationTests(unittest.TestCase):
    def test_accepts_scoped_request(self):
        request = {
            "request_id": "x",
            "operation": "memory.query",
            "project": {"owner": "seanchatmangpt", "number": 2},
        }
        self.assertEqual(("x", "memory.query"), proxy.validate_request(request, "seanchatmangpt", 2))

    def test_rejects_other_project(self):
        request = {
            "request_id": "x",
            "operation": "memory.query",
            "project": {"owner": "elsewhere", "number": 2},
        }
        with self.assertRaises(proxy.ProxyError) as ctx:
            proxy.validate_request(request, "seanchatmangpt", 2)
        self.assertEqual("REFUSED", ctx.exception.standing)
        self.assertEqual("PROJECT_SCOPE_VIOLATION", ctx.exception.reason)

    def test_rejects_raw_graphql_operation(self):
        request = {"request_id": "x", "operation": "graphql.raw"}
        with self.assertRaises(proxy.ProxyError):
            proxy.validate_request(request, "seanchatmangpt", 2)


class NormalizeTests(unittest.TestCase):
    def test_normalize_preserves_key_and_tags(self):
        title, body, meta = proxy.normalize_record(
            {
                "key": "k",
                "title": "T",
                "body": "B",
                "tags": ["b", "a", "a"],
                "kind": "dfcm.run",
            },
            None,
        )
        self.assertEqual("T", title)
        self.assertEqual("B", body)
        self.assertEqual("k", meta["key"])
        self.assertEqual(["a", "b"], meta["tags"])
        self.assertEqual("dfcm.run", meta["kind"])
        self.assertEqual("chatgpt-project-memory/v1", meta["schema"])


if __name__ == "__main__":
    unittest.main()
