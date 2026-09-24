import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COURT_FILES = [
    "scripts/verify-autonomic-contract.py",
    "versions.toml",
    "manufacturing/ontology.ttl",
    "manufacturing/ggen.toml",
    "capsules/autonomic-manufacturing/capsule.toml",
]

spec = importlib.util.spec_from_file_location("refresh_capability_sources", ROOT / "scripts" / "refresh-capability-sources.py")
refresh = importlib.util.module_from_spec(spec)
sys.modules["refresh_capability_sources"] = refresh
assert spec.loader is not None
spec.loader.exec_module(refresh)


class BootstrapCourtTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        for rel in COURT_FILES:
            dest = self.tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel, old, new, count=1):
        path = self.tmp / rel
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, count))

    def court(self):
        return subprocess.run(
            [sys.executable, str(self.tmp / "scripts/verify-autonomic-contract.py")],
            capture_output=True, text=True,
        )

    def assertRefused(self, fragment):
        result = self.court()
        self.assertEqual(result.returncode, 65, result.stdout + result.stderr)
        self.assertIn("REFUSED_AUTONOMIC_CONTRACT", result.stderr)
        self.assertIn(fragment, result.stderr)

    def test_live_tree_is_admitted(self):
        result = self.court()
        self.assertEqual(result.returncode, 0, result.stderr)
        capsule = tomllib.loads((self.tmp / "capsules/autonomic-manufacturing/capsule.toml").read_text())
        count = len(capsule["required_sources"])
        self.assertIn(f"sources={count} ", result.stdout)

    def test_capsule_source_set_drift_is_refused(self):
        required = tomllib.loads((self.tmp / "capsules/autonomic-manufacturing/capsule.toml").read_text())["required_sources"]
        self.edit("capsules/autonomic-manufacturing/capsule.toml", f'  "{required[-1]}",\n', "")
        self.assertRefused("source set drift between ontology and capsule.toml")

    def test_dropping_manufacturing_core_is_refused(self):
        ontology = (self.tmp / "manufacturing/ontology.ttl").read_text()
        block = re.search(r"^cc:GgenLegacy a cc:CapabilitySource ;.*?\s\.\n\n", ontology, re.S | re.M).group(0)
        ontology = ontology.replace(block, "").replace("cc:GgenLegacy, ", "")
        (self.tmp / "manufacturing/ontology.ttl").write_text(ontology)
        self.edit("capsules/autonomic-manufacturing/capsule.toml", '  "ggen-legacy",\n', "")
        self.assertRefused("manufacturing core dropped")

    def test_dropping_strategic_source_is_refused(self):
        ontology = (self.tmp / "manufacturing/ontology.ttl").read_text()
        block = re.search(r"^cc:EngineeringStandards a cc:CapabilitySource ;.*?\s\.\n\n", ontology, re.S | re.M).group(0)
        ontology = ontology.replace(block, "").replace("cc:EngineeringStandards, ", "")
        (self.tmp / "manufacturing/ontology.ttl").write_text(ontology)
        self.edit("capsules/autonomic-manufacturing/capsule.toml", '  "engineering-standards",\n', "")
        self.assertRefused("strategic portfolio source dropped")

    def test_declared_but_not_included_source_is_refused(self):
        ontology = (self.tmp / "manufacturing/ontology.ttl").read_text()
        self.assertIn("cc:FrozenDuckdb, ", ontology)
        (self.tmp / "manufacturing/ontology.ttl").write_text(
            ontology.replace("cc:FrozenDuckdb, ", "", 1)
        )
        self.assertRefused("cc:includesSource")

    def test_bootstrap_sha_drift_is_refused(self):
        versions = (self.tmp / "versions.toml").read_text()
        current = re.search(r'ggen_sha = "([0-9a-f]{40})"', versions).group(1)
        self.edit("versions.toml", current, "0" * 40)
        self.assertRefused("bootstrap ggen SHA differs")

    def test_release_drift_is_refused(self):
        self.edit("manufacturing/ggen.toml", 'version = "', 'version = "0.', 1)
        self.assertRefused("project.version differs from release")

    def test_non_owner_repository_is_refused(self):
        self.edit("manufacturing/ontology.ttl", 'cc:repository "seanchatmangpt/bcinr"', 'cc:repository "someone-else/bcinr"')
        self.assertRefused("repository must be seanchatmangpt/bcinr")

    def test_short_sha_is_refused(self):
        ontology = (self.tmp / "manufacturing/ontology.ttl").read_text()
        sha = re.search(r'skos:prefLabel "truex" ;.*?cc:commitSha "([0-9a-f]{40})"', ontology, re.S).group(1)
        self.edit("manufacturing/ontology.ttl", sha, sha[:12])
        self.assertRefused("truex commitSha is not an exact 40-hex SHA")

    def test_private_identity_projection_is_refused(self):
        self.edit(
            "manufacturing/ontology.ttl",
            'cc:admissionBasis "project-memory-workstream" .',
            'cc:admissionBasis "project-memory-workstream" ;\n  cc:accessClass "private" .',
        )
        self.assertRefused("private source engineering-standards forbidden by private identity projection fence")

    def test_unknown_access_class_is_refused(self):
        self.edit(
            "manufacturing/ontology.ttl",
            'cc:admissionBasis "project-memory-workstream" .',
            'cc:admissionBasis "project-memory-workstream" ;\n  cc:accessClass "secret" .',
        )
        self.assertRefused("unknown accessClass secret")

    def test_missing_lfs_law_is_refused(self):
        self.edit("manufacturing/ontology.ttl", '  cc:lfsObjectPolicy "pointer-identity" ;\n', "")
        self.assertRefused("Git LFS law missing")

    def test_ambient_do_token_is_refused(self):
        self.edit("manufacturing/ontology.ttl", "cc:requiresExternalExecution true ;", "cc:requiresExternalExecution true ;\n  cc:doAuthority true ;")
        self.assertRefused("forbidden authority token")


class RefreshRepinTests(unittest.TestCase):
    ONTOLOGY = (
        'cc:A a cc:CapabilitySource ;\n  skos:prefLabel "a" ;\n  cc:repository "seanchatmangpt/a" ;\n'
        '  cc:commitSha "' + "a" * 40 + '" ;\n  cc:role "first." .\n\n'
        'cc:B a cc:CapabilitySource ;\n  skos:prefLabel "b" ;\n  cc:repository "seanchatmangpt/b" ;\n'
        '  cc:commitSha "' + "a" * 40 + '" ;\n  cc:role "second" .\n'
    )

    def test_admitted_sources_parses_every_block(self):
        rows = refresh.admitted_sources(self.ONTOLOGY)
        self.assertEqual([r["name"] for r in rows], ["a", "b"])
        self.assertEqual({r["admitted_sha"] for r in rows}, {"a" * 40})

    def test_repin_touches_only_the_named_block(self):
        updated = refresh.repin(self.ONTOLOGY, "B", "b" * 40)
        rows = {r["name"]: r["admitted_sha"] for r in refresh.admitted_sources(updated)}
        self.assertEqual(rows, {"a": "a" * 40, "b": "b" * 40})

    def test_repin_unknown_source_is_refused(self):
        with self.assertRaises(SystemExit):
            refresh.repin(self.ONTOLOGY, "Missing", "b" * 40)

    def test_live_ontology_parses(self):
        rows = refresh.admitted_sources((ROOT / "manufacturing/ontology.ttl").read_text())
        self.assertTrue({"ggen", "ggen-marketplace", "swarmsh", "swarmsh-v2"} <= {r["name"] for r in rows})
        self.assertEqual(len(rows), len({r["repository"] for r in rows}))


if __name__ == "__main__":
    unittest.main()
