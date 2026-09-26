"""Court over the step scripts of .github/workflows/remote-relay-live-leg.yml.

Defect this guards (PR #44 integrate receipt, step "Native XaaS relay admission
and replay court"): the embedded .exs script called
``Code.require_file("lib/xaas/ultracode/remote_relay.ex")`` in its body and then
built ``%Envelope{...}``. Elixir expands struct literals while compiling the
script, before the body runs, so the step failed with
``CompileError: ...Envelope.__struct__/1 is undefined`` on every toolchain.

Two layers, Chicago style (real YAML, real elixir, real XaaS source; no doubles):

1. Static scanner: an Elixir heredoc that expands a struct literal must not rely
   on Code.require_file/compile_file inside the same script, and every file the
   ``elixir -r`` preload names must be a real path in the XaaS subject.
2. Dynamic court: when elixir and the pinned XaaS subject are available, the
   exact bash text of the workflow step is executed and must print
   XAAS_REMOTE_RELAY_ALIVE; the pre-fix text must fail with the CompileError
   (falsifier). Without elixir the dynamic tests skip with a named reason,
   unless RELAY_WORKFLOW_COURT_REQUIRE_ELIXIR=1 (as in the workflow), where a
   missing toolchain is a failure, not a skip.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "remote-relay-live-leg.yml"
NATIVE_STEP = "Native XaaS relay admission and replay court"
ALIVE_MARKER = "XAAS_REMOTE_RELAY_ALIVE"
RELAY_SOURCE = "lib/xaas/ultracode/remote_relay.ex"

HEREDOC = re.compile(r"<<'?(?P<tag>[A-Z_]+)'?\n(?P<body>.*?)\n\s*(?P=tag)\s*$", re.S | re.M)
STRUCT_LITERAL = re.compile(r"%(?P<mod>[A-Z][A-Za-z0-9_]*(?:\.[A-Z][A-Za-z0-9_]*)*)\{")
RUNTIME_LOAD = re.compile(r"\bCode\.(?:require_file|compile_file|eval_file)\s*\(")
ELIXIR_CMD = re.compile(r"^\s*elixir\b(?P<args>[^\n]*)$", re.M)
# Structs whose modules ship with Elixir/OTP and are always loadable.
CORE_STRUCTS = frozenset({
    "Date", "DateTime", "NaiveDateTime", "Time", "URI", "Range", "MapSet", "Regex",
    "Version", "Version.Requirement", "File.Stat", "IO.Stream", "Task", "Stream",
})


def load_workflow(path: pathlib.Path = WORKFLOW) -> dict:
    return yaml.safe_load(path.read_text())


def step_run(workflow: dict, name: str) -> str:
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if step.get("name") == name:
                return step["run"]
    raise KeyError(name)


def preloaded_files(run: str) -> list[str]:
    """Paths passed to `elixir -r/-pr` in the step's elixir invocations."""
    files = []
    for match in ELIXIR_CMD.finditer(run):
        tokens = match.group("args").split()
        for flag, value in zip(tokens, tokens[1:]):
            if flag in ("-r", "-pr"):
                files.append(value)
    return files


def find_struct_preload_violations(run: str) -> list[str]:
    """Findings for Elixir heredocs whose struct literals depend on runtime loading."""
    findings = []
    for doc in HEREDOC.finditer(run):
        if doc.group("tag") != "ELIXIR":
            continue
        body = doc.group("body")
        structs = sorted({m.group("mod") for m in STRUCT_LITERAL.finditer(body)} - CORE_STRUCTS)
        if structs and RUNTIME_LOAD.search(body):
            findings.append(
                "struct literal(s) %s expand at compile time but the module is loaded by "
                "Code.require_file/compile_file inside the same script" % ",".join(structs)
            )
        if structs and not RUNTIME_LOAD.search(body) and not preloaded_files(run):
            # Allowed only under `mix run` (the project is compiled and loaded).
            if not re.search(r"^\s*mix run\b", run, re.M):
                findings.append(
                    "struct literal(s) %s with no -r preload and no mix run" % ",".join(structs)
                )
    return findings


BROKEN_FORM = """set -euo pipefail
cat > /tmp/court.exs <<'ELIXIR'
Code.require_file(Path.expand("lib/xaas/ultracode/remote_relay.ex"))
alias Xaas.Ultracode.RemoteRelay.Envelope
envelope = %Envelope{command_id: "c"}
ELIXIR
elixir /tmp/court.exs
"""


class StructPreloadScannerTests(unittest.TestCase):
    def test_workflow_elixir_steps_have_no_struct_preload_violation(self):
        workflow = load_workflow()
        findings = []
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                for finding in find_struct_preload_violations(step.get("run", "") or ""):
                    findings.append(f"{step.get('name')}: {finding}")
        self.assertEqual(findings, [])

    def test_native_step_preloads_the_relay_source(self):
        run = step_run(load_workflow(), NATIVE_STEP)
        self.assertIn(RELAY_SOURCE, preloaded_files(run))
        self.assertIn(ALIVE_MARKER, run)

    def test_scanner_flags_the_pre_fix_form(self):
        findings = find_struct_preload_violations(BROKEN_FORM)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("Envelope", findings[0])
        self.assertIn("Code.require_file", findings[0])

    def test_scanner_flags_struct_with_no_preload_at_all(self):
        run = "cat > /tmp/x.exs <<'ELIXIR'\nx = %Xaas.Thing{}\nELIXIR\nelixir /tmp/x.exs\n"
        findings = find_struct_preload_violations(run)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("no -r preload", findings[0])

    def test_scanner_flags_compile_file_and_qualified_struct(self):
        run = (
            "cat > /tmp/x.exs <<'ELIXIR'\nCode.compile_file(\"lib/a.ex\")\n"
            "x = %A.B.C{}\nELIXIR\nelixir -r lib/a.ex /tmp/x.exs\n"
        )
        findings = find_struct_preload_violations(run)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("A.B.C", findings[0])

    def test_scanner_accepts_maps_core_structs_and_mix_run(self):
        maps_only = (
            "cat > /tmp/x.exs <<'ELIXIR'\nCode.require_file(\"lib/a.ex\")\n"
            "x = %{\"a\" => 1}\ny = %URI{}\nELIXIR\nelixir /tmp/x.exs\n"
        )
        self.assertEqual(find_struct_preload_violations(maps_only), [])
        mix = "cat > /tmp/s.exs <<'ELIXIR'\nx = %Xaas.Accounts.Org{}\nELIXIR\nmix run /tmp/s.exs\n"
        self.assertEqual(find_struct_preload_violations(mix), [])

    def test_scanner_ignores_non_elixir_heredocs(self):
        run = "cat > /tmp/r.json <<JSON\n{\"a\": \"%Envelope{\"}\nJSON\n"
        self.assertEqual(find_struct_preload_violations(run), [])

    def test_preload_parser_reads_only_elixir_invocations(self):
        run = "mix run -r nope.ex x.exs\nelixir -r a.ex -pr b.ex s.exs\n"
        self.assertEqual(preloaded_files(run), ["a.ex", "b.ex"])


def xaas_subject() -> pathlib.Path | None:
    candidates = [os.environ.get("XAAS_SUBJECT_DIR"), str(ROOT.parent / "xaas")]
    for candidate in candidates:
        if candidate and (pathlib.Path(candidate) / RELAY_SOURCE).is_file():
            return pathlib.Path(candidate)
    return None


def run_step_script(run: str, xaas: pathlib.Path) -> subprocess.CompletedProcess:
    """Execute a workflow step's bash text, with /tmp/ redirected to a private dir."""
    with tempfile.TemporaryDirectory() as tmp:
        text = run.replace("/tmp/", tmp + "/")
        return subprocess.run(
            ["bash", "-c", text],
            cwd=xaas,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )


class NativeStepExecutionCourt(unittest.TestCase):
    def setUp(self):
        self.xaas = xaas_subject()
        missing = []
        if shutil.which("elixir") is None:
            missing.append("elixir not on PATH")
        if self.xaas is None:
            missing.append(f"XaaS subject with {RELAY_SOURCE} not found (set XAAS_SUBJECT_DIR)")
        if missing:
            reason = "; ".join(missing)
            if os.environ.get("RELAY_WORKFLOW_COURT_REQUIRE_ELIXIR") == "1":
                self.fail("REQUIRED toolchain/subject missing: " + reason)
            self.skipTest(reason)

    def test_exact_native_step_text_prints_alive(self):
        completed = run_step_script(step_run(load_workflow(), NATIVE_STEP), self.xaas)
        self.assertEqual(completed.returncode, 0, completed.stderr[-3000:])
        self.assertIn(ALIVE_MARKER, completed.stdout)

    def test_pre_fix_form_fails_with_struct_compile_error(self):
        # Falsifier: the pre-fix step body (require_file inside the script, no -r)
        # must still fail on this toolchain, so the fix is load-bearing.
        run = step_run(load_workflow(), NATIVE_STEP)
        broken = run.replace(
            "<<'ELIXIR'\n",
            "<<'ELIXIR'\nCode.require_file(Path.expand(\"%s\"))\n" % RELAY_SOURCE,
            1,
        ).replace("elixir -r %s " % RELAY_SOURCE, "elixir ")
        self.assertNotEqual(broken, run)
        completed = run_step_script(broken, self.xaas)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("__struct__/1 is undefined", completed.stderr)
        self.assertNotIn(ALIVE_MARKER, completed.stdout)


if __name__ == "__main__":
    unittest.main()
