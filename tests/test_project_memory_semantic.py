import importlib.util
import pathlib
import sys
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "project_memory_semantic.py"
spec = importlib.util.spec_from_file_location("project_memory_semantic", SCRIPT)
semantic = importlib.util.module_from_spec(spec)
sys.modules["project_memory_semantic"] = semantic
assert spec.loader is not None
spec.loader.exec_module(semantic)

PROJECT = {"owner": "seanchatmangpt", "number": 2, "title": "Project Two", "url": "https://example.test/p2"}
ITEMS = [
    {
        "item_id": "I1",
        "is_archived": False,
        "type": "DRAFT_ISSUE",
        "content": {"id": "D1", "title": "Frontier", "body": "encoded", "url": None, "number": None, "repository": None, "state": None, "labels": [], "assignees": []},
        "field_values": {"Status": "Active"},
    },
    {
        "item_id": "I2",
        "is_archived": False,
        "type": "ISSUE",
        "content": {"id": "X2", "title": "Plain issue mentions depends_on but it is prose", "body": "depends_on memory/b", "url": "https://example.test/i/2", "number": 2, "repository": "seanchatmangpt/example", "state": "OPEN", "labels": [{"name": "bug", "color": "ff0000"}], "assignees": ["sean"]},
        "field_values": {},
    },
    {"item_id": "I3", "is_archived": False, "type": "DRAFT_ISSUE", "content": {"id": "D3", "title": "Ledger", "body": "encoded", "labels": [], "assignees": []}, "field_values": {}},
]
MEMORY = [
    {
        "item_id": "I1",
        "content_id": "D1",
        "title": "Frontier",
        "body": "Human readable frontier",
        "is_archived": False,
        "metadata": {
            "key": "dfcm/frontier/current",
            "kind": "dfcm.frontier",
            "standing": "ALIVE",
            "cell": "PORTFOLIO",
            "tags": ["frontier"],
            "capabilities": ["semantic-memory"],
            "depends_on": ["dfcm/ledger/current"],
            "updated_at": "2026-08-25T00:00:00Z",
        },
    },
    {
        "item_id": "I3",
        "content_id": "D3",
        "title": "Ledger",
        "body": "ledger",
        "is_archived": False,
        "metadata": {"key": "dfcm/ledger/current", "kind": "dfcm.ledger", "updated_at": "2026-08-24T00:00:00Z"},
    },
]


class SemanticProjectionTests(unittest.TestCase):
    def setUp(self):
        self.model = semantic.build_model(PROJECT, ITEMS, MEMORY)

    def test_memory_identity_is_stable_key(self):
        ids = {node["id"] for node in self.model["nodes"]}
        self.assertIn("memory:dfcm/frontier/current", ids)
        self.assertNotIn("item:I1", ids)

    def test_explicit_memory_relation_becomes_edge(self):
        edges = {(e["source"], e["predicate"], e["target"]) for e in self.model["edges"]}
        self.assertIn(("memory:dfcm/frontier/current", "dependsOn", "memory:dfcm/ledger/current"), edges)

    def test_free_prose_does_not_create_semantic_edge(self):
        issue_edges = [e for e in self.model["edges"] if e["source"] == "item:I2"]
        self.assertFalse(any(e["predicate"] == "dependsOn" for e in issue_edges))

    def test_table_view_is_non_graph_inspectable(self):
        table = semantic.table_view(self.model)
        row = next(row for row in table["rows"] if row["id"] == "item:I2")
        self.assertEqual("seanchatmangpt/example", row["repository"])
        self.assertEqual("OPEN", row["state"])

    def test_triples_view_projects_same_edges(self):
        triples = semantic.triples_view(self.model, include_properties=False)["triples"]
        self.assertIn({"subject": "memory:dfcm/frontier/current", "predicate": "dependsOn", "object": "memory:dfcm/ledger/current", "object_type": "iri"}, triples)

    def test_catalog_exposes_explicit_capabilities(self):
        catalog = semantic.catalog_view(self.model)
        ids = {node["id"] for node in catalog["catalog"]["Capability"]}
        self.assertIn("capability:semantic-memory", ids)

    def test_context_can_retrieve_memory_record_only(self):
        context = semantic.context_view(self.model, query="frontier", node_types=["MemoryRecord"], hops=0, limit=10)
        self.assertEqual(["memory:dfcm/frontier/current"], [node["id"] for node in context["nodes"]])

    def test_context_expands_bounded_neighborhood(self):
        context = semantic.context_view(self.model, query="Frontier", node_types=["MemoryRecord"], hops=1, limit=20)
        ids = {node["id"] for node in context["nodes"]}
        self.assertIn("memory:dfcm/ledger/current", ids)
        self.assertIn("capability:semantic-memory", ids)

    def test_process_view_does_not_claim_conformance(self):
        process = semantic.process_view(self.model)
        self.assertEqual("UNSUPPORTED_UNTIL_INDEPENDENT_VALIDATOR", process["conformance"])
        self.assertEqual(2, process["event_count"])

    def test_capability_surface_lists_virtual_views(self):
        result = semantic.capabilities_view(self.model)
        surface_ids = {surface["id"] for surface in result["virtual_surfaces"]}
        self.assertTrue({"property-graph", "triples", "table", "llm-context"} <= surface_ids)


if __name__ == "__main__":
    unittest.main()
