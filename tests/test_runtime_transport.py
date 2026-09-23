import importlib.util
import io
import json
import os
import pathlib
import shutil
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


admit = load("runtime_admit", "runtime-admit.py")
up = load("ecosystem_up", "ecosystem-up.py")


class RuntimeTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        (self.repo / "runtime").mkdir(parents=True)
        admit.ROOT, admit.RUNTIME, admit.LOCK = self.repo, self.repo / "runtime", self.repo / "runtime" / "lock.json"
        admit.PART_SIZE = 1024
        up.ROOT, up.LOCK = self.repo, self.repo / "runtime" / "lock.json"
        self.prefix = self.tmp / "prefix"
        # A real tar.gz holding one executable plus incompressible padding so it spans several parts.
        payload = self.tmp / "payload"
        (payload / "bin").mkdir(parents=True)
        tool = payload / "bin" / "hello-tool"
        tool.write_text("#!/usr/bin/env bash\necho hello-tool 1.0\n")
        tool.chmod(0o755)
        (payload / "bin" / "padding.bin").write_bytes(os.urandom(4096))
        self.archive = self.tmp / "hello-tool-x86_64.tar.gz"
        with tarfile.open(self.archive, "w:gz") as tar:
            tar.add(payload, arcname=".")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_main(self, module, argv):
        old = sys.argv
        sys.argv = [module.__name__, *argv]
        try:
            with redirect_stdout(io.StringIO()):
                return module.main()
        finally:
            sys.argv = old

    def admit_tool(self):
        self.run_main(admit, [
            "hello-tool", str(self.archive), "--version", "1.0",
            "--source-repo", "seanchatmangpt/hello-tool", "--source-sha", "a" * 40,
            "--builder", "local-container", "--layout", "bin", "--bin", "bin/hello-tool",
            "--smoke", "hello-tool | grep -q 'hello-tool 1.0'",
        ])
        return json.loads(admit.LOCK.read_text())["artifacts"]["hello-tool"]

    def up(self, *extra):
        return self.run_main(up, ["--prefix", str(self.prefix), "--quiet", *extra])

    def receipt(self):
        return json.loads((self.prefix / "ecosystem-up-receipt.json").read_text())

    def test_admission_splits_into_bounded_digest_bound_parts(self):
        spec = self.admit_tool()
        self.assertGreater(len(spec["parts"]), 1)
        self.assertTrue(all(p["size"] <= 1024 for p in spec["parts"]))
        self.assertEqual(sum(p["size"] for p in spec["parts"]), self.archive.stat().st_size)
        self.assertEqual(spec["archive"]["sha256"], admit.sha256(self.archive))

    def test_round_trip_is_alive_and_idempotent(self):
        self.admit_tool()
        self.assertEqual(self.up(), 0)
        self.assertEqual(self.receipt()["artifacts"]["hello-tool"]["standing"], "ALIVE")
        self.assertEqual(self.receipt()["artifacts"]["hello-tool"]["install"], "extracted")
        self.assertEqual(self.up(), 0)
        self.assertEqual(self.receipt()["artifacts"]["hello-tool"]["install"], "already current")
        self.assertIn("hello-tool/bin", (self.prefix / "env.sh").read_text())

    def test_tampered_part_is_build_broken(self):
        spec = self.admit_tool()
        part = self.repo / spec["parts"][1]["path"]
        part.write_bytes(b"x" + part.read_bytes()[1:])
        self.assertEqual(self.up(), 65)
        self.assertEqual(self.receipt()["artifacts"]["hello-tool"]["standing"], "BUILD_BROKEN")

    def test_missing_part_is_blocked(self):
        spec = self.admit_tool()
        (self.repo / spec["parts"][-1]["path"]).unlink()
        self.assertEqual(self.up(), 65)
        self.assertEqual(self.receipt()["artifacts"]["hello-tool"]["standing"], "BLOCKED")

    def test_env_file_is_appended(self):
        self.admit_tool()
        env_file = self.tmp / "claude-env"
        self.assertEqual(self.up("--env-file", str(env_file), "--allow-hex-network"), 0)
        self.assertIn(str(self.prefix / "env.sh"), env_file.read_text())
        self.assertIn("unset HEX_OFFLINE", (self.prefix / "env.sh").read_text())


class CommittedLockTests(unittest.TestCase):
    def test_committed_parts_match_lock(self):
        lock = json.loads((ROOT / "runtime" / "lock.json").read_text())
        for name, spec in lock["artifacts"].items():
            self.assertTrue(spec["smoke"], name)
            for part in spec["parts"]:
                path = ROOT / part["path"]
                self.assertTrue(path.is_file(), part["path"])
                self.assertEqual(path.stat().st_size, part["size"], part["path"])
                self.assertLessEqual(part["size"], lock["part_size_bytes"], part["path"])


if __name__ == "__main__":
    unittest.main()
