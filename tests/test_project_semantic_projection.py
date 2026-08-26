import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import project_semantic_projection as semantic


class SemanticProjectionTests(unittest.TestCase):
    def setUp(self):
        self.project = {
            "owner": "seanchatmangpt",
            "number": 2,
            "id": "PVT_test",
            "title": "Project Two",
            "url": "https://example.test/project/2",
        }
        self.items = [
            {
                "item_id": "PVTI_1",
                "is_archived": False,
                "type": "DRAFT_ISSUE",
                "content": {
                    "id": "DI_1",
                    "title": "DfCM frontier",
                    "body": "encoded body is removed upstream",
                    "url": None,
                    "number": None,
                    "repository": None,
                    "state": None,
                    "labels": [],
                    "assignees": [],
                },
                "field_values": {"Status": "Active", "Priority": 1},
                "memory": {
                    "body": "Current frontier",
                    "metadata": {
                        "key": "dfcm/frontier/current",
                        "kind": "dfcm.frontier",
                        "standing": "ALIVE",
                        "cell": "PORTFOLIO",
                        "tags": ["dfcm", "frontier"],
                        "repo": "seanchatmangpt/ggen-marketplace",
                        "head_sha": "0123456789abcdef0123456789abcdef01234567",
                        "memory_keys_consumed": ["dfcm/ledger/current"],
                        "created_at": "2026-08-25T16:00:00Z",
                        "updated_at": "2026-08-25T17:00:00Z",
                    },
                },
            },
            {
                "item_id": "PVTI_2",
                "is_archived": False,
                "type": "ISSUE",
                "content": {
                    "id": "I_2",
                    "title": "Consumer issue",
                    "body": "ordinary issue",
                    "url": "https://example.test/issues/2",
                    "number": 2,
                    "repository": "seanchatmangpt/ex4pm",
                    "state": "OPEN",
                    "labels": [{"name": "capability", "color": "ffffff"}],
                    "assignees": ["seanchatmangpt"],
                },
                "field_values": {"Status": "Todo"},
            },
        ]
        self.graph = semantic.build_virtual_project(
            self.project,
            self.items,
            observed_at="2026-08-25T17:49:00Z",
        )

    def test_builds_one_subject_multiple_views(self):
        self.assertEqual("project-two-semantic/v1", self.graph["schema"])
        self.assertGreaterEqual(len(self.graph["nodes"]), 8)
        self.assertGreaterEqual(len(self.graph["edges"]), 8)
        self.assertTrue(self.graph["tables"]["nodes"])
        self.assertTrue(self.graph["triples"])
        self.assertTrue(self.graph["jsonld"]["@graph"])
        self.assertEqual("virtual-semantic-paas", self.graph["services"]["model"])
        self.assertTrue(self.graph["ocel"]["objects"])

    def test_explicit_memory_relationship_becomes_edge(self):
        consumed = [edge for edge in self.graph["edges"] if edge["predicate"] == "CONSUMES_MEMORY"]
        self.assertEqual(1, len(consumed))
        self.assertTrue(consumed[0]["target"].endswith("memory:dfcm/ledger/current"))

    def test_repository_label_assignee_and_commit_nodes_are_preserved(self):
        types = {t for node in self.graph["nodes"] for t in node["types"]}
        self.assertIn("Repository", types)
        self.assertIn("Label", types)
        self.assertIn("Actor", types)
        self.assertIn("Commit", types)

    def test_no_free_prose_is_promoted_to_dependency_edge(self):
        self.items[0]["memory"]["metadata"]["body_note"] = "maybe depends on something"
        graph = semantic.build_virtual_project(self.project, self.items, observed_at="2026-08-25T17:49:00Z")
        self.assertFalse(any(edge["predicate"] == "DEPENDS_ON" and "maybe" in edge["target"] for edge in graph["edges"]))

    def test_graph_query_filters_and_neighborhood(self):
        result = semantic.query_graph(self.graph, {"kind": "dfcm.frontier", "limit": 10})
        self.assertEqual(1, result["returned_nodes"])
        node_id = result["nodes"][0]["id"]
        neighborhood = semantic.query_graph(self.graph, {"neighbors_of": [node_id], "depth": 1, "limit": 100})
        self.assertGreater(neighborhood["returned_nodes"], 1)

    def test_llm_context_is_bounded(self):
        result = semantic.context_projection(self.graph, {"text": "frontier", "types": ["MemoryRecord"], "max_body_chars": 7})
        self.assertEqual(1, result["returned_records"])
        self.assertEqual("Current", result["records"][0]["body"])

    def test_service_catalog_advertises_all_virtual_surfaces(self):
        operations = {op for capability in self.graph["services"]["capabilities"] for op in capability["operations"]}
        expected = {
            "project.graph",
            "project.graph.query",
            "project.triples",
            "project.jsonld",
            "project.tables",
            "project.services",
            "project.ocel",
            "project.context",
        }
        self.assertTrue(expected <= operations)

    def test_ocel_projection_does_not_overclaim_conformance(self):
        ocel = self.graph["ocel"]
        self.assertEqual("NOT_CLAIMED_UNTIL_INDEPENDENT_OCEL_VALIDATOR_EXECUTES", ocel["conformance"])
        event_types = {event["type"] for event in ocel["events"]}
        self.assertIn("ProjectSemanticSnapshot", event_types)
        self.assertIn("MemoryCreated", event_types)
        self.assertIn("MemoryUpdated", event_types)

    def test_select_views_refuses_unknown_projection(self):
        with self.assertRaises(ValueError):
            semantic.select_views(self.graph, ["graph", "magic"])


if __name__ == "__main__":
    unittest.main()
