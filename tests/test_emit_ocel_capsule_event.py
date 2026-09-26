"""Chicago-style test for scripts/emit-ocel-capsule-event.sh.

Runs the real script as a real subprocess against a real local HTTP server
(no mocking of the script itself, its curl call, or its Python fragments) and
asserts on the actual captured request body -- catching exactly the class of
bug this script previously had: `python3 -` reads its own program text from
stdin, so a heredoc script there silently starves a later `sys.stdin.read()`
of any data, landing an empty `{}` payload while everything else (schema,
activity, standing) looked correct. Asserting only on HTTP status or on a
hand-built Elixir envelope (as control-plane's ingestor_test.exs does) does
not exercise this path -- this test specifically does.
"""

import http.server
import json
import pathlib
import subprocess
import tempfile
import threading
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "emit-ocel-capsule-event.sh"


class CapturingHandler(http.server.BaseHTTPRequestHandler):
    captured = {}

    def do_POST(self):  # noqa: N802 (BaseHTTPRequestHandler API)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        CapturingHandler.captured["path"] = self.path
        CapturingHandler.captured["authorization"] = self.headers.get("Authorization")
        CapturingHandler.captured["body"] = json.loads(body)
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, format, *args):  # noqa: A002 - silence test output
        pass


class EmitOcelCapsuleEventTests(unittest.TestCase):
    def setUp(self):
        CapturingHandler.captured = {}
        self.server = http.server.HTTPServer(("127.0.0.1", 0), CapturingHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)

    def run_emitter(self, tmp_path, payload, **extra_args):
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(payload))
        args = [
            "bash",
            str(SCRIPT),
            "--agent-id",
            extra_args.get("agent_id", "capsule-verify:test"),
            "--run-id",
            extra_args.get("run_id", "test:run-1"),
            "--activity",
            extra_args.get("activity", "capsule.verify"),
            "--standing",
            extra_args.get("standing", "ALIVE"),
            "--occurred-at",
            "2026-08-26T00:00:00Z",
            "--payload-file",
            str(payload_file),
        ]
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "OCEL_INGEST_TOKEN": "test-token",
            "OCEL_INGEST_URL": f"http://127.0.0.1:{self.port}",
        }
        return subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)

    def test_payload_content_reaches_the_ingest_request_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            payload = {
                "capsule_name": "process-intelligence",
                "acceptance_exit_code": 0,
                "nested": {"a": [1, 2, 3]},
            }
            result = self.run_emitter(tmp_path, payload)

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("body", CapturingHandler.captured, "no request was ever received")

            envelope = CapturingHandler.captured["body"]
            self.assertEqual("chatgpt-cloud-ocel/1", envelope["schema"])
            self.assertEqual("Bearer test-token", CapturingHandler.captured["authorization"])
            self.assertEqual(1, len(envelope["events"]))
            self.assertEqual(payload, envelope["events"][0]["payload"])

    def test_missing_payload_file_defaults_to_empty_object_not_a_crash(self):
        with tempfile.TemporaryDirectory():
            args = [
                "bash",
                str(SCRIPT),
                "--agent-id",
                "capsule-verify:test",
                "--run-id",
                "test:run-2",
                "--activity",
                "capsule.verify",
                "--standing",
                "ALIVE",
                "--occurred-at",
                "2026-08-26T00:00:00Z",
            ]
            env = {
                "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
                "OCEL_INGEST_TOKEN": "test-token",
                "OCEL_INGEST_URL": f"http://127.0.0.1:{self.port}",
            }
            result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)
            self.assertEqual(0, result.returncode, msg=result.stderr)
            envelope = CapturingHandler.captured["body"]
            self.assertEqual({}, envelope["events"][0]["payload"])


if __name__ == "__main__":
    unittest.main()
