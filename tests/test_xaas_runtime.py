import importlib.util
import io
import json
import os
import pathlib
import threading
import unittest
import sys
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "xaas-runtime.py"
spec = importlib.util.spec_from_file_location("xaas_runtime", SCRIPT)
bridge = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bridge
assert spec.loader is not None
spec.loader.exec_module(bridge)

TOOLS = sorted(bridge.EXPECTED_TOOLS)


class Handler(BaseHTTPRequestHandler):
    calls = []
    tools = TOOLS
    auth_status = 200

    def log_message(self, *_):
        pass

    def _body(self):
        n = int(self.headers.get("content-length", "0"))
        return json.loads(self.rfile.read(n)) if n else None

    def _json(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = self._body()
        type(self).calls.append(("POST", self.path, self.headers.get("authorization"), body))
        if type(self).auth_status != 200:
            return self._json(type(self).auth_status, {"error": "unauthorized"})
        if self.path == "/internal-api/execution/mcp":
            method = body["method"]
            if method == "initialize":
                return self._json(200, {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "serverInfo": {"name": "xaas-ultracode-lease", "version": "1.0.0"},
                        "capabilities": {"tools": {}},
                    },
                })
            if method == "tools/list":
                return self._json(200, {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"tools": [{"name": n} for n in type(self).tools]},
                })
            if method == "tools/call":
                if body["params"]["name"] == "refuse-me":
                    return self._json(200, {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": {
                            "isError": True,
                            "content": [{"type": "text", "text": "{\"error\":\"no_authority\"}"}],
                        },
                    })
                return self._json(200, {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"content": [{"type": "text", "text": "{\"status\":\"ok\"}"}]},
                })
        if self.path == "/internal-api/execution/runs":
            return self._json(201, {
                "run_id": "run-1",
                "epoch_id": "11111111-1111-1111-1111-111111111111",
            })
        return self._json(404, {"error": "not_found"})

    def do_GET(self):
        type(self).calls.append(("GET", self.path, self.headers.get("authorization"), None))
        if self.path.startswith("/internal-api/execution/epochs/") and self.path.endswith("/receipts"):
            epoch = self.path.split("/")[4]
            return self._json(200, {
                "epoch_id": epoch,
                "receipts": [{"id": "r1", "outcome": "alive"}],
            })
        return self._json(404, {"error": "not_found"})


class XaasRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/internal-api/execution/mcp"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        Handler.calls = []
        Handler.tools = TOOLS
        Handler.auth_status = 200
        self.target = bridge.Target(self.url, "Bearer secret-value")

    def test_probe_verifies_exact_required_tool_floor_and_sends_bearer(self):
        row = bridge.probe(self.target, 2)
        self.assertEqual(row["standing"], "ALIVE")
        self.assertEqual(row["contract"]["missing"], [])
        self.assertTrue(row["authenticated"])
        self.assertEqual(
            [call[2] for call in Handler.calls],
            ["Bearer secret-value", "Bearer secret-value"],
        )
        self.assertNotIn("secret-value", json.dumps(row))

    def test_probe_missing_tool_is_unsupported(self):
        Handler.tools = [name for name in TOOLS if name != "actuate"]
        row = bridge.probe(self.target, 2)
        self.assertEqual(row["standing"], "UNSUPPORTED")
        self.assertEqual(row["reason"], "CONTRACT_MISMATCH")
        self.assertEqual(row["contract"]["missing"], ["actuate"])

    def test_submit_run_defaults_to_zcode_and_preserves_server_path(self):
        args = type("Args", (), {
            "goal": "fix it",
            "provider": "zcode",
            "worktree": None,
            "exact_subject": "repo@sha",
            "verifier_suite": "court",
            "timeout": 2,
        })()
        row = bridge.submit_run(self.target, args)
        self.assertEqual(row["standing"], "PARTIAL_ALIVE")
        self.assertEqual(row["downstream_standing"], "UNKNOWN")
        method, path, auth, body = Handler.calls[-1]
        self.assertEqual(
            (method, path, auth),
            ("POST", "/internal-api/execution/runs", "Bearer secret-value"),
        )
        self.assertEqual(body, {
            "goal": "fix it",
            "provider": "zcode",
            "exact_subject": "repo@sha",
            "verifier_suite": "court",
        })
        self.assertEqual(
            row["response"]["epoch_id"],
            "11111111-1111-1111-1111-111111111111",
        )

    def test_reads_epoch_receipts(self):
        epoch = "11111111-1111-1111-1111-111111111111"
        row = bridge.read_receipts(self.target, epoch, 2)
        self.assertEqual(row["standing"], "ALIVE")
        self.assertEqual(row["response"]["receipts"][0]["outcome"], "alive")

    def test_auth_failure_is_typed_refusal(self):
        Handler.auth_status = 401
        row = bridge.probe(self.target, 2)
        self.assertEqual(row["standing"], "REFUSED_AUTHENTICATION")
        self.assertEqual(row["reason"], "AUTHENTICATION")

    def test_mcp_tool_refusal_is_not_alive(self):
        row = bridge.mcp_call(
            self.target,
            "tools/call",
            {"name": "refuse-me", "arguments": {}},
            2,
        )
        self.assertEqual(row["standing"], "REFUSED_REQUEST")
        self.assertEqual(row["reason"], "TOOL_REFUSAL")

    def test_network_failure_is_blocked_not_refused(self):
        target = bridge.Target(
            "http://127.0.0.1:1/internal-api/execution/mcp",
            None,
        )
        row = bridge.probe(target, 0.1)
        self.assertEqual(row["standing"], "BLOCKED")
        self.assertEqual(row["reason"], "NETWORK")

    def test_successful_submit_has_zero_exit_at_partial_alive_scope(self):
        self.assertEqual(bridge.exit_code({"standing": "PARTIAL_ALIVE"}), 0)

    def test_actuate_requires_explicit_do_ack_before_network(self):
        old = dict(os.environ)
        os.environ["XAAS_MCP_URL"] = self.url
        os.environ["XAAS_MCP_TOKEN"] = "secret-value"
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                code = bridge.main([
                    "mcp",
                    "tools/call",
                    "--tool",
                    "actuate",
                    "--arguments",
                    "{}",
                ])
        finally:
            os.environ.clear()
            os.environ.update(old)
        row = json.loads(out.getvalue())
        self.assertEqual(code, 77)
        self.assertEqual(row["standing"], "REFUSED_AUTHORITY")
        self.assertEqual(row["reason"], "EXPLICIT_DO_ACK_REQUIRED")
        self.assertEqual(Handler.calls, [])

    def test_base_url_refuses_unknown_mcp_shape(self):
        with self.assertRaises(ValueError):
            _ = bridge.Target("https://example.com/other", None).base_url


if __name__ == "__main__":
    unittest.main()
