import importlib.util
import io
import json
import os
import pathlib
import threading
import tempfile
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
        if self.path == "/redirect/internal-api/execution/mcp":
            self.send_response(307)
            self.send_header("location", "/stolen")
            self.send_header("content-length", "0")
            self.end_headers()
            return None
        if self.path == "/plain/internal-api/execution/mcp":
            return self._json(200, ["not", "json-rpc"])
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
        if self.path.startswith("/plain/"):
            return self._json(200, ["not", "an", "object"])
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


    def request_file(self, document, *, filename=None, require_config=False):
        temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(temp.name)
        request_id = document.get("request_id", "request") if isinstance(document, dict) else "request"
        request = root / (filename or f"{request_id}.json")
        receipt = root / "receipts" / f"{request.stem}.receipt.json"
        request.write_text(json.dumps(document))
        args = type("A", (), {
            "request": request,
            "receipt": receipt,
            "timeout": 2,
            "require_config": require_config,
        })()
        return temp, args, receipt

    def test_request_file_probe_round_trip_writes_receipt(self):
        doc = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "probe-1",
            "operation": "fabric.probe",
            "payload": {},
        }
        temp, args, receipt = self.request_file(doc)
        old = dict(os.environ)
        os.environ["XAAS_MCP_URL"] = self.url
        os.environ["XAAS_MCP_TOKEN"] = "secret-value"
        try:
            row = bridge.run_request_file(args)
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.addCleanup(temp.cleanup)
        self.assertEqual(row["standing"], "ALIVE")
        self.assertEqual(row["request_id"], "probe-1")
        self.assertEqual(row["request_document_sha256"], bridge.digest(doc))
        self.assertEqual(json.loads(receipt.read_text())["standing"], "ALIVE")
        self.assertNotIn("secret-value", receipt.read_text())

    def test_request_submit_requires_exact_subject_without_network(self):
        doc = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "submit-no-subject",
            "operation": "run.submit",
            "payload": {"goal": "fix it"},
        }
        row = bridge.execute_request_document(doc, self.target, 2)
        self.assertEqual(row["standing"], "REFUSED_REQUEST")
        self.assertEqual(row["reason"], "EXACT_SUBJECT_REQUIRED")
        self.assertEqual(row["request_document_sha256"], bridge.digest(doc))
        self.assertEqual(Handler.calls, [])

    def test_request_submit_refuses_non_zcode_provider_without_network(self):
        doc = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "submit-other-provider",
            "operation": "run.submit",
            "payload": {"goal": "fix it", "exact_subject": "repo@sha", "provider": "other"},
        }
        row = bridge.execute_request_document(doc, self.target, 2)
        self.assertEqual(row["standing"], "REFUSED_REQUEST")
        self.assertEqual(row["reason"], "PROVIDER_UNSUPPORTED")
        self.assertEqual(Handler.calls, [])

    def test_request_file_filename_mismatch_still_writes_receipt(self):
        doc = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "canonical-id",
            "operation": "fabric.probe",
            "payload": {},
        }
        temp, args, receipt = self.request_file(doc, filename="wrong-name.json")
        self.addCleanup(temp.cleanup)
        row = bridge.run_request_file(args)
        self.assertEqual(row["standing"], "REFUSED_REQUEST")
        self.assertEqual(row["reason"], "REQUEST_FILENAME_MISMATCH")
        self.assertEqual(row["request_document_sha256"], bridge.digest(doc))
        self.assertEqual(json.loads(receipt.read_text())["reason"], "REQUEST_FILENAME_MISMATCH")
        self.assertEqual(Handler.calls, [])

    def test_request_file_require_config_blocks_without_secrets_and_writes_receipt(self):
        doc = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "missing-config",
            "operation": "fabric.probe",
            "payload": {},
        }
        temp, args, receipt = self.request_file(doc, require_config=True)
        self.addCleanup(temp.cleanup)
        old = dict(os.environ)
        os.environ.pop("XAAS_MCP_URL", None)
        os.environ.pop("XAAS_MCP_TOKEN", None)
        try:
            row = bridge.run_request_file(args)
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertEqual(row["standing"], "BLOCKED")
        self.assertEqual(row["reason"], "IRREDUCIBLE_TRANSPORT_CONFIG")
        self.assertIn("XAAS_MCP_URL", row["detail"])
        self.assertIn("XAAS_MCP_TOKEN", row["detail"])
        self.assertEqual(json.loads(receipt.read_text())["standing"], "BLOCKED")
        self.assertEqual(Handler.calls, [])

    def test_request_epoch_receipts_validates_uuid_before_network(self):
        bad = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "bad-epoch",
            "operation": "epoch.receipts",
            "payload": {"epoch_id": "not-a-uuid"},
        }
        row = bridge.execute_request_document(bad, self.target, 2)
        self.assertEqual(row["standing"], "REFUSED_REQUEST")
        self.assertEqual(row["reason"], "EPOCH_ID_INVALID")
        self.assertEqual(Handler.calls, [])

        good = dict(bad)
        good["request_id"] = "good-epoch"
        good["payload"] = {"epoch_id": "11111111-1111-1111-1111-111111111111"}
        row = bridge.execute_request_document(good, self.target, 2)
        self.assertEqual(row["standing"], "ALIVE")
        self.assertEqual(row["response"]["receipts"][0]["outcome"], "alive")


    def run_main(self, argv, env):
        old = dict(os.environ)
        os.environ.pop("XAAS_MCP_URL", None)
        os.environ.pop("XAAS_MCP_TOKEN", None)
        os.environ.update(env)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                code = bridge.main(argv)
        finally:
            os.environ.clear()
            os.environ.update(old)
        return code, json.loads(out.getvalue())

    def test_direct_require_config_blocks_before_localhost_default(self):
        # Observed in Claude Code Cloud: without XAAS_* the direct probe fell
        # back to localhost:4000 and reported NETWORK, misattributing the edge.
        for command in (["probe"], ["receipts", "11111111-1111-1111-1111-111111111111"]):
            code, row = self.run_main(["--require-config", *command], {})
            self.assertEqual(code, 69)
            self.assertEqual(row["standing"], "BLOCKED")
            self.assertEqual(row["reason"], "IRREDUCIBLE_TRANSPORT_CONFIG")
            self.assertEqual(row["detail"], "missing environment: XAAS_MCP_URL,XAAS_MCP_TOKEN")
            self.assertEqual(row["target_source"], "default")
            self.assertIsNone(row["endpoint"])
            self.assertNotIn("request_id", row)
        self.assertEqual(Handler.calls, [])

    def test_direct_require_config_blocks_on_missing_token_only(self):
        code, row = self.run_main(["--require-config", "probe"], {"XAAS_MCP_URL": self.url})
        self.assertEqual(row["reason"], "IRREDUCIBLE_TRANSPORT_CONFIG")
        self.assertEqual(row["detail"], "missing environment: XAAS_MCP_TOKEN")
        self.assertEqual(Handler.calls, [])

    def test_direct_require_config_passes_through_when_configured(self):
        code, row = self.run_main(
            ["--require-config", "probe"],
            {"XAAS_MCP_URL": self.url, "XAAS_MCP_TOKEN": "secret-value"},
        )
        self.assertEqual(code, 0)
        self.assertEqual(row["standing"], "ALIVE")
        self.assertEqual(row["target_source"], "env")
        self.assertNotIn("secret-value", json.dumps(row))

    def test_direct_probe_records_flag_target_source(self):
        # Local-dev default is preserved, but the receipt names where the target came from.
        code, row = self.run_main(["--url", self.url, "probe"], {})
        self.assertEqual(row["target_source"], "flag")
        self.assertEqual(row["standing"], "ALIVE")

    def test_actuate_do_fence_survives_require_config(self):
        code, row = self.run_main(
            ["--require-config", "mcp", "tools/call", "--tool", "actuate", "--arguments", "{}"],
            {"XAAS_MCP_URL": self.url, "XAAS_MCP_TOKEN": "secret-value"},
        )
        self.assertEqual(code, 77)
        self.assertEqual(row["reason"], "EXPLICIT_DO_ACK_REQUIRED")
        self.assertEqual(Handler.calls, [])

    def test_redirect_is_refused_and_bearer_not_replayed(self):
        base = self.url.rsplit("/internal-api/", 1)[0]
        target = bridge.Target(base + "/redirect/internal-api/execution/mcp", "Bearer secret-value")
        row = bridge.probe(target, 2)
        self.assertEqual(row["standing"], "BLOCKED")
        self.assertEqual(row["reason"], "REDIRECT_REFUSED")
        self.assertEqual([c[1] for c in Handler.calls], ["/redirect/internal-api/execution/mcp"])
        self.assertNotIn("secret-value", json.dumps(row))

    def test_url_userinfo_is_refused_before_network_and_never_receipted(self):
        port = self.url.split(":")[2].split("/")[0]
        target = bridge.Target(
            f"http://user:hunter2@127.0.0.1:{port}/internal-api/execution/mcp", "Bearer secret-value"
        )
        row = bridge.probe(target, 2)
        self.assertEqual(row["standing"], "BLOCKED")
        self.assertEqual(row["reason"], "IRREDUCIBLE_TRANSPORT_CONFIG")
        self.assertEqual(Handler.calls, [])
        dumped = json.dumps(row)
        for secret in ("hunter2", "user:", "127.0.0.1", port):
            self.assertNotIn(secret, dumped)

    def test_receipt_endpoint_redacts_secret_derived_host(self):
        row = bridge.probe(self.target, 2)
        self.assertEqual(row["endpoint"], "http://<redacted-host>/internal-api/execution/mcp")
        self.assertNotIn("127.0.0.1", json.dumps(row))
        self.assertEqual(len(row["endpoint_sha256"]), 64)
        self.assertEqual(row["endpoint_sha256"], bridge.endpoint_digest(self.url))

    def test_2xx_without_json_rpc_envelope_is_not_alive(self):
        base = self.url.rsplit("/internal-api/", 1)[0]
        target = bridge.Target(base + "/plain/internal-api/execution/mcp", "Bearer secret-value")
        row = bridge.probe(target, 2)
        self.assertEqual(row["standing"], "BUILD_BROKEN")
        self.assertEqual(row["reason"], "PROTOCOL_SHAPE")
        row = bridge.read_receipts(target, "11111111-1111-1111-1111-111111111111", 2)
        self.assertEqual(row["standing"], "BUILD_BROKEN")
        self.assertEqual(row["reason"], "PROTOCOL_SHAPE")

    def test_http_protocol_violation_is_typed_not_crash(self):
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        def serve():
            conn, _ = srv.accept()
            conn.recv(65536)
            conn.sendall(b"GARBAGE\r\n\r\n")
            conn.close()

        t = threading.Thread(target=serve, daemon=True)
        t.start()
        target = bridge.Target(f"http://127.0.0.1:{port}/internal-api/execution/mcp", None)
        row = bridge.probe(target, 2)
        t.join(timeout=2)
        srv.close()
        self.assertEqual(row["standing"], "BUILD_BROKEN")
        self.assertEqual(row["reason"], "PROTOCOL")

    def test_request_mode_bad_url_shape_still_writes_receipt(self):
        doc = {
            "schema": bridge.REQUEST_SCHEMA,
            "request_id": "bad-shape",
            "operation": "epoch.receipts",
            "payload": {"epoch_id": "11111111-1111-1111-1111-111111111111"},
        }
        temp, args, receipt = self.request_file(doc, require_config=True)
        self.addCleanup(temp.cleanup)
        old = dict(os.environ)
        os.environ["XAAS_MCP_URL"] = "http://127.0.0.1:1/mcp"
        os.environ["XAAS_MCP_TOKEN"] = "secret-value"
        try:
            row = bridge.run_request_file(args)
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertEqual(row["standing"], "BLOCKED")
        self.assertEqual(row["reason"], "IRREDUCIBLE_TRANSPORT_CONFIG")
        self.assertEqual(json.loads(receipt.read_text())["request_id"], "bad-shape")
        self.assertNotIn("secret-value", receipt.read_text())

    def test_direct_submit_bad_url_shape_is_typed_not_crash(self):
        code, row = self.run_main(
            ["receipts", "11111111-1111-1111-1111-111111111111"],
            {"XAAS_MCP_URL": "http://127.0.0.1:1/mcp", "XAAS_MCP_TOKEN": "secret-value"},
        )
        self.assertEqual(code, 69)
        self.assertEqual(row["reason"], "IRREDUCIBLE_TRANSPORT_CONFIG")

    def test_actuate_fence_is_case_and_space_insensitive(self):
        for name in ("Actuate", " ACTUATE ", "actuate"):
            code, row = self.run_main(
                ["mcp", "tools/call", "--tool", name, "--arguments", "{}"],
                {"XAAS_MCP_URL": self.url, "XAAS_MCP_TOKEN": "secret-value"},
            )
            self.assertEqual(code, 77, name)
            self.assertEqual(row["reason"], "EXPLICIT_DO_ACK_REQUIRED")
        self.assertEqual(Handler.calls, [])

RESOLVER = ROOT / "scripts" / "xaas-runtime-requests.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "xaas-runtime-proxy.yml"


class RelayRequestResolverTests(unittest.TestCase):
    def setUp(self):
        import subprocess
        self.sp = subprocess
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = pathlib.Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        (self.repo / "xaas-runtime" / "requests").mkdir(parents=True)
        (self.repo / "xaas-runtime" / "receipts").mkdir(parents=True)
        (self.repo / "README").write_text("base\n")
        self.base = self.commit("base")

    def git(self, *args):
        return self.sp.run(["git", *args], cwd=self.repo, check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def add_request(self, name):
        (self.repo / "xaas-runtime" / "requests" / name).write_text("{}\n")

    def resolve(self, **env):
        full = {"PATH": os.environ["PATH"], "EVENT_NAME": "push", **env}
        proc = self.sp.run(["bash", str(RESOLVER)], cwd=self.repo, env=full, capture_output=True, text=True)
        return proc.returncode, proc.stdout.split(), proc.stderr

    def test_push_resolves_only_added_requests(self):
        self.add_request("a.json")
        after = self.commit("req")
        code, out, _ = self.resolve(BEFORE_SHA=self.base, AFTER_SHA=after)
        self.assertEqual((code, out), (0, ["xaas-runtime/requests/a.json"]))

    def test_receipted_request_is_never_re_executed(self):
        self.add_request("a.json")
        after = self.commit("req")
        (self.repo / "xaas-runtime" / "receipts" / "a.receipt.json").write_text("{}\n")
        code, out, err = self.resolve(BEFORE_SHA=self.base, AFTER_SHA=after)
        self.assertEqual((code, out), (0, []))
        self.assertIn("SKIPPED[ALREADY_RECEIPTED]", err)
        code, out, err = self.resolve(DISPATCH_PATH="xaas-runtime/requests/a.json", AFTER_SHA=after)
        self.assertEqual((code, out), (0, []))

    def test_unreachable_or_zero_before_falls_back_to_unreceipted_set(self):
        self.add_request("a.json")
        self.add_request("b.json")
        (self.repo / "xaas-runtime" / "receipts" / "a.receipt.json").write_text("{}\n")
        after = self.commit("reqs")
        for before in ("0" * 40, "deadbeef" * 5, ""):
            code, out, err = self.resolve(BEFORE_SHA=before, AFTER_SHA=after)
            self.assertEqual((code, out), (0, ["xaas-runtime/requests/b.json"]), before)
            self.assertIn("BEFORE_UNRESOLVABLE", err)

    def test_nested_and_traversal_paths_are_refused(self):
        nested = self.repo / "xaas-runtime" / "requests" / "sub"
        nested.mkdir()
        (nested / "x.json").write_text("{}\n")
        (self.repo / "versions.json").write_text("{}\n")
        after = self.commit("nested")
        code, out, _ = self.resolve(BEFORE_SHA=self.base, AFTER_SHA=after)
        self.assertEqual(out, [])
        for bad in (
            "xaas-runtime/requests/../../versions.json",
            "xaas-runtime/requests/sub/x.json",
            "versions.json",
            'x"; echo PWNED; echo "',
        ):
            code, out, err = self.resolve(DISPATCH_PATH=bad, AFTER_SHA=after)
            self.assertEqual(code, 2, bad)
            self.assertEqual(out, [], bad)
            self.assertIn("REFUSED[REQUEST_PATH_OUT_OF_SCOPE]", err)
            self.assertNotIn("PWNED", err.replace(bad, ""))

    def test_symlinked_request_is_refused(self):
        (self.repo / "secret.json").write_text("{}\n")
        (self.repo / "xaas-runtime" / "requests" / "link.json").symlink_to("../../secret.json")
        after = self.commit("link")
        code, out, err = self.resolve(BEFORE_SHA=self.base, AFTER_SHA=after)
        self.assertEqual(out, [])
        self.assertIn("REFUSED[REQUEST_PATH_SYMLINK]", err)

    def test_workflow_never_interpolates_expressions_into_run_scripts(self):
        in_run = False
        run_indent = 0
        offenders = []
        for number, line in enumerate(WORKFLOW.read_text().splitlines(), 1):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if in_run and stripped and indent <= run_indent:
                in_run = False
            if stripped.startswith("run:"):
                in_run, run_indent = True, indent
                if "${{" in stripped:
                    offenders.append(number)
                continue
            if in_run and "${{" in line:
                offenders.append(number)
        self.assertEqual(offenders, [])

    def test_secrets_are_scoped_to_the_execute_step_only(self):
        text = WORKFLOW.read_text()
        self.assertEqual(text.count("secrets.XAAS_MCP_TOKEN"), 1)
        self.assertEqual(text.count("secrets.XAAS_MCP_URL"), 1)
        execute = text.index("- name: Execute bounded XaaS requests")
        self.assertGreater(text.index("secrets.XAAS_MCP_TOKEN"), execute)
        self.assertLess(text.index("secrets.XAAS_MCP_TOKEN"), text.index("- name:", execute + 1))
        self.assertNotIn("actuate", text)


class FabricReceiptParityTests(unittest.TestCase):
    """Golden parity: Python canonical_json must digest the fixture shared with the
    Elixir client (xaas-runtime/elixir) and xaas Xaas.Tunnel.Receipt byte-identically."""

    GOLDEN = ROOT / "xaas-runtime" / "elixir" / "test" / "fixtures" / "receipt_golden.json"
    EXPECTED = GOLDEN.with_suffix(".sha256")

    def test_golden_receipt_digest_matches_elixir_client(self):
        value = json.loads(self.GOLDEN.read_text(encoding="utf-8"))
        expected = self.EXPECTED.read_text().strip()
        self.assertEqual(bridge.digest(value), expected)
        self.assertEqual(expected, "7d98905d89388c098e14c63226356f8b4cab61d6422c1017ea77e78162ef2870")

    def test_golden_mutation_changes_digest(self):
        value = json.loads(self.GOLDEN.read_text(encoding="utf-8"))
        value["identity"]["idempotency_key"] = "golden-002"
        self.assertNotEqual(bridge.digest(value), self.EXPECTED.read_text().strip())


if __name__ == "__main__":
    unittest.main()
