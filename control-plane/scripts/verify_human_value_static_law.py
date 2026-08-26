#!/usr/bin/env python3
"""Fail closed when canned business value can reach the human-value runtime surface."""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "lib/chatgpt_cloud_control_plane/human_value/provider.ex",
    ROOT / "lib/chatgpt_cloud_control_plane/human_value/world.ex",
    ROOT / "lib/chatgpt_cloud_control_plane_web/live/human_value_live.ex",
]

FORBIDDEN_WORDS = re.compile(r"\b(todo|tbd|placeholder|lorem|acme|demo|sample|example)\b", re.IGNORECASE)
STATIC_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?:[T ][0-9:.+-Z]+)?\b")
STATIC_MONEY = re.compile(r"(?:\$|USD\s+)\d[\d,]*(?:\.\d{2})?")

findings: list[dict[str, object]] = []

for path in FILES:
    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        for reason, pattern in (
            ("PLACEHOLDER_REFUSED", FORBIDDEN_WORDS),
            ("STATIC_CURRENTNESS_REFUSED", STATIC_DATE),
            ("STATIC_BUSINESS_METRIC_REFUSED", STATIC_MONEY),
        ):
            match = pattern.search(line)
            if match:
                findings.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "line": line_no,
                        "reason": reason,
                        "literal": match.group(0),
                    }
                )

receipt = {
    "schema": "human-value-static-court/v1",
    "checked_files": [str(path.relative_to(ROOT)) for path in FILES],
    "static_placeholder_defects": len(findings),
    "findings": findings,
    "standing": "ALIVE" if not findings else "VALUE_REFUSED",
    "allowed_constants": [
        "route names",
        "Ash action/resource identities",
        "receipt schema versions",
        "SYNTHETIC evidence label",
        "ISO currency code",
        "synthetic.invalid reserved domain",
        "generator bounds and policy constants",
    ],
}

print(json.dumps(receipt, sort_keys=True))
sys.exit(0 if not findings else 1)
