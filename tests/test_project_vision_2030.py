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
                    "key": "vision/manufacturing",
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
                    "key": "vision/cloud-gym",
                    "standing": "PARTIAL_ALIVE",
                    "repo": "seanchatmangpt/gymact",
                    "tags": ["cloud", "aws", "azure", "gcp", "gym", "benchmark", "ci"],
                    "requires": "vision/manufacturing",
                },
            ),
            self.item(
                "C",
                "Unresolved consumer",
                {
                    "key": "vision/consumer",
                    "standing": "UNKNOWN",
                    "repo": "seanchatmangpt/autofde",
                    "dependencies": "vision/missing-capability",
                },
            ),
        ]
        self.graph = semantic.build_virtual_project(
            self.project,
            self.items,
            observed_at="2026-08-26T02:00:00Z",
        )

    def test_projects_capability_evidence_and_dependency_closure(self):
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
        self.assertTrue(any(item["memory_key"] == "vision/manufacturing" for item in projection["frontier"]))

    def test_minimum_evidence_turns_single_signal_into_explicit_gap(self):
        projection = vision_2030.project(self.graph, {"minimum_evidence": 4})
        pillars = {pillar["id"]: pillar for pillar in projection["capability_coverage"]["pillars"]}
        self.assertEqual("GAP", pillars["semantic-interoperability"]["status"])
        self.assertEqual(4, pillars["semantic-interoperability"]["minimum_evidence"])

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
