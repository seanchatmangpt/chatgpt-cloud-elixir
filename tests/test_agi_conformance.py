"""The conformance court's own falsifiers, run against a temp rail with trivial guards.

Never runs the real guard set (so no recursion). Each test proves one refusal or standing
path of scripts/verify-agi-conformance.py.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ConformanceCourtTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "scripts").mkdir()
        shutil.copy2(ROOT / "scripts/verify-agi-conformance.py", self.tmp / "scripts")
        shutil.copytree(ROOT / "governance", self.tmp / "governance",
                        ignore=shutil.ignore_patterns("__pycache__"))
        conf = self.tmp / "governance/agi-academy-conformance.toml"
        # Replace every real guard command with `true`; keep ids, proves, and mappings.
        conf.write_text(re.sub(r'^command = ".*"$', 'command = "true"', conf.read_text(), flags=re.M))
        ledger = self.tmp / "governance/failure-ledger.toml"
        ledger.write_text(re.sub(r'^refs = \[.*\]$', 'refs = ["governance/failure-ledger.toml"]', ledger.read_text(), flags=re.M))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def court(self):
        receipt = self.tmp / "receipt.json"
        proc = subprocess.run([sys.executable, str(self.tmp / "scripts/verify-agi-conformance.py"), "--receipt", str(receipt)],
                              capture_output=True, text=True)
        return proc, (json.loads(receipt.read_text()) if receipt.exists() else None)

    def edit(self, rel, old, new):
        path = self.tmp / rel
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def test_all_guards_passing_is_alive(self):
        proc, receipt = self.court()
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertEqual(receipt["standing"], "ALIVE")
        self.assertEqual(len(receipt["modules"]), 11)
        self.assertIn("does not certify", " ".join(receipt["non_claims"]))

    def test_failing_guard_breaks_exactly_its_mappings(self):
        conf = self.tmp / "governance/agi-academy-conformance.toml"
        text = conf.read_text()
        text = text.replace('[guards.release-court]\ncommand = "true"', '[guards.release-court]\ncommand = "exit 7"')
        conf.write_text(text)
        proc, receipt = self.court()
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertEqual(receipt["standing"], "PARTIAL_ALIVE")
        self.assertEqual(receipt["guards"]["release-court"]["exit"], 7)
        self.assertEqual(receipt["modules"]["evidence-qualification"], "BUILD_BROKEN")
        self.assertEqual(receipt["modules"]["brce"], "ALIVE")

    def test_unmapped_academy_module_is_refused(self):
        self.edit("governance/agi-academy-conformance.toml", "[modules.brce]", "[modules.brce-renamed]")
        proc, receipt = self.court()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("REFUSED:UNMAPPED_MODULES:brce", proc.stdout)
        self.assertIn("REFUSED:UNKNOWN_MODULES:brce-renamed", proc.stdout)
        self.assertIsNone(receipt)

    def test_unguarded_invariant_is_refused(self):
        conf = self.tmp / "governance/agi-academy-conformance.toml"
        text = conf.read_text()
        text = re.sub(r'(\[invariants\.zero_unreceipted_actuation\]\n)guards = \[.*\]', r'\1guards = []', text)
        conf.write_text(text)
        proc, _ = self.court()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("REFUSED:UNGUARDED:invariants.zero_unreceipted_actuation", proc.stdout)

    def test_vendored_academy_drift_is_refused(self):
        verifier = self.tmp / "governance/agi-academy/verify_agi_academy.py"
        verifier.write_text(verifier.read_text() + "\n# drift\n")
        proc, _ = self.court()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("REFUSED:VENDORED_DIGEST_DRIFT:verify_agi_academy.py", proc.stdout)

    def test_ledger_entry_without_known_guard_is_refused(self):
        self.edit("governance/failure-ledger.toml", 'guards = ["rail-guard-tests"]', 'guards = ["nonexistent-guard"]')
        proc, _ = self.court()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("LEDGER_UNKNOWN_GUARD", proc.stdout)

    def test_ledger_ref_must_exist(self):
        self.edit("governance/failure-ledger.toml", 'refs = ["governance/failure-ledger.toml"]', 'refs = ["no/such/file"]')
        proc, _ = self.court()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("LEDGER_REF_MISSING", proc.stdout)


if __name__ == "__main__":
    unittest.main()
