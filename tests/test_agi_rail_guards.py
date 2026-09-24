"""Executable guards for the AGI Academy invariants and terminal refusals on this rail.

Each test is a permanent guard referenced by governance/agi-academy-conformance.toml or
governance/failure-ledger.toml. They run real scripts and parse real files; no mocks.
"""
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ZeroUnreceiptedActuationTests(unittest.TestCase):
    def deploy_steps(self):
        workflow = yaml.safe_load((WORKFLOWS / "deploy-fly.yml").read_text())
        return workflow["jobs"]["deploy"]["steps"]

    def test_deploy_always_emits_and_uploads_a_receipt(self):
        steps = {s.get("name"): s for s in self.deploy_steps()}
        emit = steps["Emit deployment receipt"]
        upload = steps["Upload deployment receipt"]
        self.assertEqual(emit.get("if"), "always()")
        self.assertEqual(upload.get("if"), "always()")
        self.assertEqual(upload["with"]["path"], "deploy-receipt.json")
        self.assertEqual(upload["with"]["if-no-files-found"], "error")
        names = [s.get("name") for s in self.deploy_steps()]
        self.assertGreater(names.index("Emit deployment receipt"), names.index("Deploy exact GitHub subject"))

    def test_deploy_receipt_standing_follows_observed_outcomes(self):
        script = {s.get("name"): s for s in self.deploy_steps()}["Emit deployment receipt"]["run"]
        cases = {
            ("failure", "skipped", "skipped"): "BLOCKED",
            ("success", "failure", "skipped"): "BUILD_BROKEN",
            ("success", "success", "failure"): "BUILD_BROKEN",
            ("success", "success", "success"): "ALIVE",
        }
        for (authority, deploy, health), expected in cases.items():
            with tempfile.TemporaryDirectory() as tmp:
                tmp = pathlib.Path(tmp)
                if health == "success":
                    (tmp / "healthz.json").write_text('{"status":"ok"}')
                env = {"PATH": "/usr/bin:/bin", "RUNNER_TEMP": str(tmp), "GITHUB_REPOSITORY": "o/r",
                       "AUTHORITY": authority, "DEPLOY": deploy, "HEALTH": health, "SUBJECT_SHA": "a" * 40,
                       "RUN_URL": "u", "TRIGGER": "push", "ACTOR": "x", "CONFIGURED_APP": "app"}
                subprocess.run(["bash", "-c", script], cwd=tmp, env=env, check=True, capture_output=True)
                receipt = json.loads((tmp / "deploy-receipt.json").read_text())
                self.assertEqual(receipt["standing"], expected, (authority, deploy, health))
                self.assertEqual(receipt["subject"]["sha"], "a" * 40)
                self.assertEqual(receipt["healthz_sha256"] is not None, health == "success")

    def test_graph_mutation_without_receipt_is_refused(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/refresh-capability-sources.py"), "--write"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--write requires --receipt", proc.stderr)

    def test_memory_writes_are_receipted(self):
        workflow = (WORKFLOWS / "project-memory-proxy.yml").read_text()
        self.assertIn("project-memory/receipts", workflow)


class ExactSubjectTests(unittest.TestCase):
    def test_workflows_fetch_sources_only_through_the_canonical_fetcher(self):
        autonomic = (WORKFLOWS / "autonomic-manufacturing.yml").read_text()
        self.assertIn("scripts/fetch-capability-sources.sh", autonomic)
        self.assertNotIn('while IFS=$\'\\t\' read -r name repository sha', autonomic)

    def test_fetcher_refuses_a_malformed_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = pathlib.Path(tmp) / "lock.json"
            lock.write_text(json.dumps({"sources": [{"name": "x", "repository": "o/r", "sha": "abc123"}]}))
            proc = subprocess.run(["bash", str(ROOT / "scripts/fetch-capability-sources.sh"), str(lock), str(pathlib.Path(tmp) / "d")],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("REFUSED", proc.stderr)

    def test_committed_runtime_binds_exact_sources_and_builders(self):
        lock = json.loads((ROOT / "runtime/lock.json").read_text())
        for name, spec in lock["artifacts"].items():
            self.assertRegex(spec["source"]["sha"], r"^[0-9a-f]{40}$", name)
            self.assertIn(spec["provenance"]["builder"], {"upstream-release", "local-container", "github-actions"}, name)
            self.assertRegex(spec["archive"]["sha256"], r"^[0-9a-f]{64}$", name)

    def test_process_intelligence_readme_mirrors_capsule_pins(self):
        cfg = tomllib.loads((ROOT / "capsules/process-intelligence/capsule.toml").read_text())
        readme = (ROOT / "capsules/process-intelligence/README.md").read_text()
        pins = [cfg["subjects"]["ash_r2rml"], cfg["subjects"]["ex4pm"], cfg["dependencies"]["wasm4pm_compat"]]
        for pin in pins:
            self.assertIn(f"`{pin['sha']}` / tree `{pin['tree_sha']}`", readme)


class ProjectionAndReuseTests(unittest.TestCase):
    def test_generated_projections_are_never_tracked(self):
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "manufacturing/generated", "manufacturing/.ggen"],
                                 capture_output=True, text=True)
        if tracked.returncode != 0:
            self.skipTest("not a git checkout")
        self.assertEqual(tracked.stdout.strip(), "")

    def test_vendored_academy_is_byte_identical_to_its_pin(self):
        provenance = tomllib.loads((ROOT / "governance/agi-academy/PROVENANCE.toml").read_text())
        for item in provenance["file"]:
            digest = hashlib.sha256((ROOT / "governance/agi-academy" / item["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, item["sha256"], item["path"])

    def test_ash_fixture_declares_string_length_mode(self):
        config = (ROOT / "fixtures/ash_ets_smoke/config/config.exs").read_text()
        self.assertRegex(config, r"config :ash, default_string_length_count: :(codepoints|mixed)")


class AdvisoryGuardTests(unittest.TestCase):
    advisories = load_script("check_advisories", "check-advisories.py")

    def test_every_pin_is_queried_against_hex(self):
        pins = self.advisories.pinned_packages(tomllib.loads((ROOT / "versions.toml").read_text()))
        query = self.advisories.batch_query(pins)
        self.assertEqual(len(query["queries"]), len(pins))
        self.assertTrue(all(q["package"]["ecosystem"] == "Hex" for q in query["queries"]))

    def test_findings_are_attributed_per_pin(self):
        pins = [("ash", "3.32.0"), ("spark", "2.7.3")]
        response = {"results": [{"vulns": [{"id": "EEF-CVE-2026-82737"}, {"id": "EEF-CVE-2026-82736"}]}, {}]}
        findings = self.advisories.advisories_from_batch(pins, response)
        self.assertEqual(findings, {"ash@3.32.0": ["EEF-CVE-2026-82736", "EEF-CVE-2026-82737"], "spark@2.7.3": []})

    def test_short_osv_response_is_refused(self):
        with self.assertRaises(ValueError):
            self.advisories.advisories_from_batch([("ash", "1"), ("spark", "2")], {"results": [{}]})


if __name__ == "__main__":
    unittest.main()
