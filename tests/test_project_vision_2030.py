import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_semantic_projection as semantic
import project_vision_2030 as vision_2030


class Vision2030ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.project = {
            "owner": "seanchatmangpt",
            "number": 2,
            "id": "PVT_test",
            "title": "Project Two",
            "url": "https://example.test/project/2",
        }
        self.items = [
            self.item(
                "A",
                "Manufacturing frontier",
                {
                    "key": "project/vision/manufacturing",
                    "standing": "ALIVE",
                    "repo": "seanchatmangpt/ggen-marketplace",
                    "tags": ["ggen", "ontology", "receipt", "semantic"],
                    "head_sha": "0123456789abcdef0123456789abcdef01234567",
                    "receipt": "dfcm/receipt/manufacturing",
                },
            ),
            self.item(
                "B",
                "Cloud gym qualification",
                {
                    "key": "project/vision/cloud-gym",
                    "standing": "PARTIAL_ALIVE",
                    "repo": "seanchatmangpt/gymact",
                    "tags": ["cloud", "aws", "azure", "gcp", "gym", "benchmark", "ci"],
                    "requires": "project/vision/manufacturing",
                },
            ),
            self.item(
                "C",
                "Unresolved consumer",
                {
                    "key": "project/vision/consumer",
                    "standing": "UNKNOWN",
                    "repo": "seanchatmangpt/autofde",
                    "dependencies": "project/vision/missing-capability",
                },
            ),
        ]
        self.graph = semantic.build_virtual_project(
            self.project,
            self.items,
            observed_at="2026-08-26T02:00:00Z",
        )

    def test_projects_capability_evidence_dependency_capital_and_option_space(self):
        projection = vision_2030.project(self.graph)

        self.assertEqual("project-two-vision-2030/v1", projection["schema"])
        self.assertEqual("AUTONOMIC_SOFTWARE_MANUFACTURING", projection["objective"])
        self.assertEqual(2030, projection["horizon"])
        self.assertEqual("READ_ONLY_VIRTUAL_PROJECTION", projection["authority"])
        self.assertEqual(0, projection["admission"]["mutating_operations_introduced"])
        self.assertFalse(projection["admission"]["standing_granted"])
        self.assertFalse(projection["admission"]["consequential_do_authority"])

        self.assertEqual(3, projection["portfolio"]["memory_records"])
        self.assertGreaterEqual(projection["portfolio"]["repositories"], 3)
        self.assertEqual(3, projection["evidence_coverage"]["standing"]["count"])
        self.assertEqual(1, projection["evidence_coverage"]["commit_identity"]["count"])
        self.assertEqual(1, projection["evidence_coverage"]["receipt_or_replay"]["count"])

        closure = projection["dependency_closure"]
        self.assertEqual(2, closure["dependency_edges"])
        self.assertEqual(1, closure["resolved_edges"])
        self.assertEqual(1, closure["unresolved_edges"])
        self.assertEqual(0.5, closure["closure_ratio"])

        pillars = {pillar["id"]: pillar for pillar in projection["capability_coverage"]["pillars"]}
        self.assertEqual("PRESENT", pillars["deterministic-manufacture"]["status"])
        self.assertEqual("PRESENT", pillars["agent-evaluation"]["status"])
        self.assertTrue(any(item["memory_key"] == "project/vision/manufacturing" for item in projection["frontier"]))

        capital = projection["manufacturing_capital"]
        self.assertGreaterEqual(capital["capital_records"], 2)
        self.assertEqual(1, capital["qualified_reusable_capital"])
        self.assertGreater(capital["capital_ratio"], 0.0)
        self.assertTrue(capital["by_class"])

        option_space = projection["combinatorial_option_space"]
        self.assertEqual(28, option_space["possible_pairings"])
        self.assertGreater(option_space["observed_pairings"], 0)
        self.assertGreater(option_space["cross_pillar_records"], 0)

        envelope = projection["autonomy_envelope"]
        self.assertEqual("OPEN", envelope["status"])
        self.assertEqual("ASSEMBLY_IN_PROGRESS", envelope["structural_phase"])
        self.assertIn("UNRESOLVED_DEPENDENCIES", envelope["falsifiers"])
        self.assertTrue(projection["maximalist_frontier"])

    def test_minimum_evidence_turns_single_signal_into_explicit_gap(self):
        projection = vision_2030.project(self.graph, {"minimum_evidence": 4})
        pillars = {pillar["id"]: pillar for pillar in projection["capability_coverage"]["pillars"]}
        self.assertEqual("GAP", pillars["semantic-interoperability"]["status"])
        self.assertEqual(4, pillars["semantic-interoperability"]["minimum_evidence"])
        self.assertIn("EVIDENCE_SHORTFALL", pillars["semantic-interoperability"]["falsifiers"])

    def test_domain_diversity_prevents_repeated_single_repo_evidence_from_goodharting_a_pillar(self):
        projection = vision_2030.project(self.graph, {"minimum_domains": 2})
        pillars = {pillar["id"]: pillar for pillar in projection["capability_coverage"]["pillars"]}
        deterministic = pillars["deterministic-manufacture"]
        self.assertEqual(1, deterministic["domain_count"])
        self.assertEqual(2, deterministic["minimum_domains"])
        self.assertEqual("GAP", deterministic["status"])
        self.assertIn("DOMAIN_DIVERSITY_SHORTFALL", deterministic["falsifiers"])

    def test_closed_autonomy_envelope_requires_structural_evidence_but_never_grants_authority(self):
        complete_items = [
            self.item(
                "Z",
                "Integrated autonomic stack",
                {
                    "key": "project/vision/integrated-stack",
                    "standing": "ALIVE",
                    "repo": "seanchatmangpt/autonomic-stack",
                    "tags": [
                        "ggen",
                        "receipt",
                        "ci",
                        "cloud",
                        "process",
                        "semantic",
                        "gym",
                        "memory",
                    ],
                    "head_sha": "fedcba9876543210fedcba9876543210fedcba98",
                    "receipt": "dfcm/receipt/integrated-stack",
                },
            )
        ]
        graph = semantic.build_virtual_project(
            self.project,
            complete_items,
            observed_at="2026-08-26T03:00:00Z",
        )

        projection = vision_2030.project(graph, {"minimum_receipt_ratio": 1.0})
        self.assertEqual(8, projection["capability_coverage"]["present_pillars"])
        self.assertEqual("CLOSED", projection["autonomy_envelope"]["status"])
        self.assertEqual("INTEGRATED_AUTONOMIC_STACK", projection["autonomy_envelope"]["structural_phase"])
        self.assertEqual([], projection["autonomy_envelope"]["falsifiers"])
        self.assertEqual("OBSERVATIONAL_ONLY", projection["autonomy_envelope"]["standing"])
        self.assertFalse(projection["admission"]["standing_granted"])
        self.assertFalse(projection["admission"]["consequential_do_authority"])

    @staticmethod
    def item(item_id, title, metadata):
        return {
            "item_id": item_id,
            "is_archived": False,
            "type": "DRAFT_ISSUE",
            "content": {
                "id": f"D_{item_id}",
                "title": title,
                "body": "",
                "url": None,
                "number": None,
                "repository": None,
                "state": None,
                "labels": [],
                "assignees": [],
            },
            "field_values": {},
            "memory": {"body": "", "metadata": metadata},
        }


if __name__ == "__main__":
    unittest.main()
