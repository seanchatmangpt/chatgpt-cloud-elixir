"""The A2A vocabulary files are sources with an executable consumer: this conformance
check binds a2a/ontology.ttl and a2a/context.jsonld to what scripts/a2a.py writes.

Real collaborators only: the module under test writes real cards and messages onto a
real bare repository; the vocabulary files are parsed from disk. A drift in either
direction (a wire field with no term, a term with no declaration, a performative the
runtime accepts but the ontology does not name) fails here.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_a2a  # noqa: E402

a2a = test_a2a.a2a
VOCAB = Path(__file__).resolve().parents[1] / "a2a"
PREFIX = "a2a:"


def ontology_terms() -> tuple[set[str], set[str], set[str]]:
    """(classes, properties, performatives) declared in ontology.ttl (subject position)."""
    classes, properties, performatives = set(), set(), set()
    for line in (VOCAB / "ontology.ttl").read_text().splitlines():
        m = re.match(r"^a2a:(\w+)\s+(.*)$", line.strip())
        if not m:
            continue
        name, rest = m.groups()
        if rest.startswith("a rdfs:Class"):
            classes.add(name)
        elif rest.startswith("a a2a:Performative"):
            performatives.add(name)
        elif "rdfs:domain" in rest or rest.startswith("a rdf:Property"):
            properties.add(name)
    return classes, properties, performatives


def context_terms() -> dict[str, str]:
    ctx = json.loads((VOCAB / "context.jsonld").read_text())["@context"]
    out = {}
    for key, value in ctx.items():
        iri = value if isinstance(value, str) else value.get("@id", "")
        out[key] = iri
    return out


class VocabularyConformanceTest(test_a2a.BusFixture):
    def test_performatives_match_the_runtime(self) -> None:
        _, _, performatives = ontology_terms()
        self.assertEqual(performatives, a2a.PERFORMATIVES)

    def test_every_wire_field_has_a_context_term_declared_in_the_ontology(self) -> None:
        self.alpha.init(["echo"])
        self.beta.init(["echo"])
        req = self.alpha.send("beta", "request", [{"kind": "text", "text": "x"}], skill="echo")
        [reply] = self.beta.serve_once()
        card = self.alpha.sync()["alpha"]["card"]
        wire = (set(card) | set(req) | set(reply)) - {"@context"}
        terms = context_terms()
        self.assertEqual(sorted(wire - set(terms)), [], "wire fields with no JSON-LD term")
        classes, properties, _ = ontology_terms()
        for field in sorted(wire):
            iri = terms[field]
            if iri.startswith("@"):
                continue
            with self.subTest(field=field):
                self.assertTrue(iri.startswith(PREFIX), iri)
                self.assertIn(iri[len(PREFIX):], properties, f"{iri} is not declared in ontology.ttl")
        # the rdf:type values the runtime writes are declared classes
        self.assertEqual({card["type"], req["type"]}, {"a2a:AgentCard", "a2a:Message"})
        self.assertLessEqual({"AgentCard", "Message"}, classes)

    def test_context_iri_is_the_runtime_context(self) -> None:
        self.assertTrue(a2a.CONTEXT.endswith("/a2a/context.jsonld"))
        self.assertTrue((VOCAB / "context.jsonld").is_file())

    def test_contested_standing_is_named_in_the_ontology(self) -> None:
        ttl = (VOCAB / "ontology.ttl").read_text()
        self.assertIn("REFUSED_CONTESTED", ttl)


if __name__ == "__main__":
    unittest.main()
