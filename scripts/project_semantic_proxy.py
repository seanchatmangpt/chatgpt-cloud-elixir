#!/usr/bin/env python3
"""Bounded read-only semantic virtualization endpoint for GitHub Project v2 #2."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from project_memory_proxy import GraphQLClient, ProjectMemoryStore, ProxyError, utc_now
from project_memory_semantic import VIEW_NAMES, build_model, render_view

ALLOWED_OPERATION = "project.semantic"


def validate_request(request: dict[str, Any], allowed_owner: str, allowed_number: int) -> tuple[str, str]:
    request_id = str(request.get("request_id", "")).strip()
    if not request_id:
        raise ProxyError("request_id is required", standing="REFUSED", reason="INVALID_REQUEST")
    operation = str(request.get("operation", "")).strip()
    if operation != ALLOWED_OPERATION:
        raise ProxyError(f"operation not allowed: {operation}", standing="REFUSED", reason="INVALID_OPERATION")
    project = request.get("project") or {}
    owner = str(project.get("owner", allowed_owner))
    number = int(project.get("number", allowed_number))
    if owner != allowed_owner or number != allowed_number:
        raise ProxyError(
            f"request targets non-admitted project {owner}/{number}",
            standing="REFUSED",
            reason="PROJECT_SCOPE_VIOLATION",
        )
    view = str((request.get("payload") or {}).get("view", "graph"))
    if view not in VIEW_NAMES:
        raise ProxyError(f"semantic view not allowed: {view}", standing="REFUSED", reason="INVALID_SEMANTIC_VIEW")
    return request_id, operation


def execute_request(store: ProjectMemoryStore, request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload") or {}
    max_items = max(1, min(int(payload.get("max_items", 5000)), 5000))
    include_archived = bool(payload.get("include_archived", False))
    types = payload.get("types")
    items, items_truncated = store.project_items(types=types, include_archived=include_archived, max_items=max_items)
    memory_records, memory_truncated = store.memory_items(include_archived=include_archived, max_items=max_items)
    project = {
        "owner": store.project.owner,
        "number": store.project.number,
        "id": store.project.node_id,
        "title": store.project.title,
        "url": store.project.url,
    }
    model = build_model(project, items, memory_records)
    result = render_view(model, str(payload.get("view", "graph")), payload)
    result["source"] = {
        "item_count": len(items),
        "memory_record_count": len(memory_records),
        "truncated": bool(items_truncated or memory_truncated),
    }
    return result


def receipt_for(request_path: Path, request: dict[str, Any], request_id: str | None, operation: str | None, token_source: str) -> dict[str, Any]:
    return {
        "schema": "chatgpt-project-semantic-receipt/v1",
        "request_path": str(request_path),
        "request_id": request_id,
        "operation": operation,
        "observed_at": utc_now(),
        "token_source": token_source,
        "standing": "UNKNOWN",
        "reason": None,
        "result": None,
        "error": None,
        "request_digest_basis": request,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)

    allowed_owner = os.environ.get("PROJECT_MEMORY_OWNER", "seanchatmangpt")
    allowed_number = int(os.environ.get("PROJECT_MEMORY_NUMBER", "2"))
    token = os.environ.get("PROJECTS_TOKEN", "")
    token_source = os.environ.get("PROJECTS_TOKEN_SOURCE", "unknown")

    request: dict[str, Any] = {}
    request_id: str | None = None
    operation: str | None = None
    exit_code = 0
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        request_id, operation = validate_request(request, allowed_owner, allowed_number)
        receipt = receipt_for(args.request, request, request_id, operation, token_source)
        client = GraphQLClient(token, token_source=token_source)
        store = ProjectMemoryStore(client, allowed_owner, allowed_number)
        receipt["result"] = execute_request(store, request)
        receipt["project"] = {
            "owner": store.project.owner,
            "number": store.project.number,
            "id": store.project.node_id,
            "title": store.project.title,
            "url": store.project.url,
        }
        receipt["standing"] = "ALIVE"
    except ProxyError as exc:
        receipt = receipt_for(args.request, request, request_id, operation, token_source)
        receipt["standing"] = exc.standing
        receipt["reason"] = exc.reason
        receipt["error"] = {"message": str(exc), "details": exc.details}
        exit_code = 2
    except Exception as exc:
        receipt = receipt_for(args.request, request, request_id, operation, token_source)
        receipt["standing"] = "BUILD_BROKEN"
        receipt["reason"] = "SEMANTIC_PROXY_FAILURE"
        receipt["error"] = {"message": f"{type(exc).__name__}: {exc}"}
        exit_code = 3

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
