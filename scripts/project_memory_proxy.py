#!/usr/bin/env python3
"""Bounded GitHub Projects v2 CRUD proxy for ChatGPT scheduled manufacturing cells.

Requests are JSON documents. Only one configured user project is admissible. Memory
records are stored as ProjectV2 draft issues with machine-readable metadata embedded
in an HTML comment. The script writes a receipt for every request and never prints a
credential.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API_URL = "https://api.github.com/graphql"
MARKER_RE = re.compile(r"^<!-- chatgpt-project-memory:v1 ([A-Za-z0-9_-]+) -->\n?", re.M)
ALLOWED_OPERATIONS = {
    "project.snapshot",
    "project.items",
    "memory.create",
    "memory.read",
    "memory.update",
    "memory.upsert",
    "memory.query",
    "memory.archive",
    "memory.delete",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64url_decode(text: str) -> bytes:
    padding = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + padding)


def encode_memory_body(metadata: dict[str, Any], body: str) -> str:
    marker = b64url_encode(json_dumps(metadata).encode("utf-8"))
    body = body.rstrip()
    return f"<!-- chatgpt-project-memory:v1 {marker} -->\n\n{body}\n" if body else f"<!-- chatgpt-project-memory:v1 {marker} -->\n"


def decode_memory_body(body: str) -> tuple[dict[str, Any] | None, str]:
    match = MARKER_RE.search(body or "")
    if not match:
        return None, body or ""
    try:
        metadata = json.loads(b64url_decode(match.group(1)).decode("utf-8"))
    except Exception:
        return None, body or ""
    cleaned = (body[: match.start()] + body[match.end() :]).lstrip("\n")
    return metadata, cleaned.rstrip()


def flatten_field_values(field_values: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten a ProjectV2 GraphQL fieldValues connection into {field_name: value}.

    Decodes each union variant (text/number/date/single-select/iteration) into a
    plain scalar or dict, keyed by the field's display name. Unrecognized/empty
    nodes are skipped. Pure function -- no network, easy to unit test.
    """
    result: dict[str, Any] = {}
    nodes = ((field_values or {}).get("nodes")) or []
    for node in nodes:
        if not node:
            continue
        field = node.get("field") or {}
        name = field.get("name")
        if not name:
            continue
        if "text" in node:
            result[name] = node.get("text")
        elif "number" in node:
            result[name] = node.get("number")
        elif "date" in node:
            result[name] = node.get("date")
        elif "startDate" in node or "duration" in node:
            result[name] = {
                "title": node.get("title"),
                "start_date": node.get("startDate"),
                "duration": node.get("duration"),
            }
        elif "name" in node:
            result[name] = node.get("name")
    return result


class ProxyError(RuntimeError):
    def __init__(self, message: str, *, standing: str = "UNKNOWN", reason: str | None = None, details: Any = None):
        super().__init__(message)
        self.standing = standing
        self.reason = reason
        self.details = details


class GraphQLError(ProxyError):
    pass


class GraphQLClient:
    def __init__(self, token: str, token_source: str = "unknown"):
        if not token:
            raise ProxyError("No GitHub token available", standing="BLOCKED", reason="IRREDUCIBLE_AUTHORITY")
        self._token = token
        self.token_source = token_source

    def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            API_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "chatgpt-cloud-elixir-project-memory-proxy/1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if exc.code in (401, 403):
                raise GraphQLError(
                    f"GitHub GraphQL authorization failed with HTTP {exc.code}",
                    standing="BLOCKED",
                    reason="IRREDUCIBLE_AUTHORITY",
                    details={"http_status": exc.code, "body": raw[:1000]},
                ) from exc
            raise GraphQLError(
                f"GitHub GraphQL HTTP failure {exc.code}", standing="UNKNOWN", reason="GITHUB_API_HTTP", details={"body": raw[:1000]}
            ) from exc
        except urllib.error.URLError as exc:
            raise GraphQLError("GitHub GraphQL network failure", standing="UNKNOWN", reason="NETWORK", details=str(exc)) from exc

        errors = data.get("errors") or []
        if errors:
            messages = " | ".join(str(error.get("message", error)) for error in errors)
            lowered = messages.lower()
            if any(term in lowered for term in ("resource not accessible", "forbidden", "permission", "scope", "could not resolve to a user")):
                standing, reason = "BLOCKED", "IRREDUCIBLE_AUTHORITY"
            else:
                standing, reason = "UNKNOWN", "GRAPHQL_ERROR"
            raise GraphQLError(messages, standing=standing, reason=reason, details=errors)
        return data.get("data") or {}


@dataclass(frozen=True)
class ProjectRef:
    owner: str
    number: int
    node_id: str
    title: str
    url: str


class ProjectMemoryStore:
    def __init__(self, client: GraphQLClient, allowed_owner: str, allowed_number: int):
        self.client = client
        self.allowed_owner = allowed_owner
        self.allowed_number = allowed_number
        self.project = self._resolve_project()

    def _resolve_project(self) -> ProjectRef:
        query = """
        query($login:String!, $number:Int!) {
          user(login:$login) {
            projectV2(number:$number) { id title url }
          }
        }
        """
        data = self.client.execute(query, {"login": self.allowed_owner, "number": self.allowed_number})
        user = data.get("user")
        project = user and user.get("projectV2")
        if not project:
            raise ProxyError("Configured project was not visible", standing="BLOCKED", reason="IRREDUCIBLE_AUTHORITY")
        return ProjectRef(self.allowed_owner, self.allowed_number, project["id"], project.get("title", ""), project.get("url", ""))

    def list_items(self, *, max_items: int = 5000) -> tuple[list[dict[str, Any]], bool]:
        query = """
        query($project:ID!, $after:String) {
          node(id:$project) {
            ... on ProjectV2 {
              items(first:100, after:$after) {
                nodes {
                  id
                  isArchived
                  type
                  content {
                    ... on DraftIssue { id title body }
                    ... on Issue {
                      id title body url number
                      state
                      repository { nameWithOwner }
                      labels(first: 20) { nodes { name color } }
                      assignees(first: 10) { nodes { login } }
                    }
                    ... on PullRequest {
                      id title body url number
                      state
                      repository { nameWithOwner }
                      labels(first: 20) { nodes { name color } }
                      assignees(first: 10) { nodes { login } }
                    }
                  }
                  fieldValues(first: 20) {
                    nodes {
                      ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2FieldCommon { name } } }
                      ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2FieldCommon { name } } }
                      ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2FieldCommon { name } } }
                      ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } }
                      ... on ProjectV2ItemFieldIterationValue { title startDate duration field { ... on ProjectV2FieldCommon { name } } }
                    }
                  }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
        """
        items: list[dict[str, Any]] = []
        after: str | None = None
        truncated = False
        while True:
            data = self.client.execute(query, {"project": self.project.node_id, "after": after})
            conn = ((data.get("node") or {}).get("items") or {})
            nodes = conn.get("nodes") or []
            for item in nodes:
                if item:
                    items.append(item)
                    if len(items) >= max_items:
                        truncated = bool(conn.get("pageInfo", {}).get("hasNextPage")) or len(nodes) > 0
                        return items[:max_items], truncated
            page = conn.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                break
            after = page.get("endCursor")
            if not after:
                break
        return items, truncated

    def project_items(
        self, *, types: list[str] | None = None, include_archived: bool = False, max_items: int = 5000
    ) -> tuple[list[dict[str, Any]], bool]:
        items, truncated = self.list_items(max_items=max_items)
        allowed_types = {str(t).upper() for t in types} if types else None
        result: list[dict[str, Any]] = []
        for item in items:
            if item.get("isArchived") and not include_archived:
                continue
            item_type = item.get("type")
            if allowed_types is not None and item_type not in allowed_types:
                continue
            content = item.get("content") or {}
            labels = [
                {"name": node.get("name"), "color": node.get("color")}
                for node in ((content.get("labels") or {}).get("nodes") or [])
                if node
            ]
            assignees = [node.get("login") for node in ((content.get("assignees") or {}).get("nodes") or []) if node]
            result.append(
                {
                    "item_id": item.get("id"),
                    "is_archived": bool(item.get("isArchived")),
                    "type": item_type,
                    "content": {
                        "id": content.get("id"),
                        "title": content.get("title") or "",
                        "body": content.get("body") or "",
                        "url": content.get("url"),
                        "number": content.get("number"),
                        "repository": (content.get("repository") or {}).get("nameWithOwner"),
                        "state": content.get("state"),
                        "labels": labels,
                        "assignees": assignees,
                    },
                    "field_values": flatten_field_values(item.get("fieldValues")),
                }
            )
        return result, truncated

    def memory_items(self, *, include_archived: bool = False, max_items: int = 5000) -> tuple[list[dict[str, Any]], bool]:
        items, truncated = self.list_items(max_items=max_items)
        result: list[dict[str, Any]] = []
        for item in items:
            if item.get("isArchived") and not include_archived:
                continue
            content = item.get("content") or {}
            metadata, text = decode_memory_body(content.get("body") or "")
            if not metadata:
                continue
            result.append(
                {
                    "item_id": item.get("id"),
                    "content_id": content.get("id"),
                    "title": content.get("title") or "",
                    "body": text,
                    "is_archived": bool(item.get("isArchived")),
                    "metadata": metadata,
                }
            )
        return result, truncated

    def find_by_key(self, key: str, *, include_archived: bool = True) -> dict[str, Any] | None:
        records, _ = self.memory_items(include_archived=include_archived)
        matches = [record for record in records if record.get("metadata", {}).get("key") == key]
        if not matches:
            return None
        matches.sort(key=lambda r: str(r.get("metadata", {}).get("updated_at", "")), reverse=True)
        return matches[0]

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        key = require_key(record)
        if self.find_by_key(key, include_archived=True):
            raise ProxyError(f"Memory key already exists: {key}", standing="REFUSED", reason="DUPLICATE_MEMORY_KEY")
        title, body, metadata = normalize_record(record, existing=None)
        query = """
        mutation($project:ID!, $title:String!, $body:String!) {
          addProjectV2DraftIssue(input:{projectId:$project,title:$title,body:$body}) {
            projectItem { id content { ... on DraftIssue { id title body } } }
          }
        }
        """
        data = self.client.execute(query, {"project": self.project.node_id, "title": title, "body": encode_memory_body(metadata, body)})
        item = (data.get("addProjectV2DraftIssue") or {}).get("projectItem") or {}
        return self._record_from_mutation(item)

    def update(self, key: str, record: dict[str, Any]) -> dict[str, Any]:
        existing = self.find_by_key(key, include_archived=True)
        if not existing:
            raise ProxyError(f"Memory key not found: {key}", standing="REFUSED", reason="MEMORY_NOT_FOUND")
        content_id = existing.get("content_id")
        if not content_id:
            raise ProxyError("Memory item is not an updatable draft issue", standing="REFUSED", reason="NON_DRAFT_MEMORY")
        merged = dict(record)
        merged["key"] = key
        title, body, metadata = normalize_record(merged, existing=existing)
        query = """
        mutation($draft:ID!, $title:String!, $body:String!) {
          updateProjectV2DraftIssue(input:{draftIssueId:$draft,title:$title,body:$body}) {
            draftIssue { id title body }
          }
        }
        """
        data = self.client.execute(query, {"draft": content_id, "title": title, "body": encode_memory_body(metadata, body)})
        draft = (data.get("updateProjectV2DraftIssue") or {}).get("draftIssue") or {}
        return {
            "item_id": existing.get("item_id"),
            "content_id": draft.get("id", content_id),
            "title": draft.get("title", title),
            "body": body,
            "is_archived": existing.get("is_archived", False),
            "metadata": metadata,
        }

    def upsert(self, record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        key = require_key(record)
        existing = self.find_by_key(key, include_archived=True)
        if existing:
            return "updated", self.update(key, record)
        return "created", self.create(record)

    def archive(self, key: str) -> dict[str, Any]:
        existing = self.find_by_key(key, include_archived=True)
        if not existing:
            raise ProxyError(f"Memory key not found: {key}", standing="REFUSED", reason="MEMORY_NOT_FOUND")
        if existing.get("is_archived"):
            return existing
        query = """
        mutation($project:ID!, $item:ID!) {
          archiveProjectV2Item(input:{projectId:$project,itemId:$item}) { item { id isArchived } }
        }
        """
        self.client.execute(query, {"project": self.project.node_id, "item": existing["item_id"]})
        existing["is_archived"] = True
        return existing

    def delete(self, key: str) -> dict[str, Any]:
        existing = self.find_by_key(key, include_archived=True)
        if not existing:
            raise ProxyError(f"Memory key not found: {key}", standing="REFUSED", reason="MEMORY_NOT_FOUND")
        query = """
        mutation($project:ID!, $item:ID!) {
          deleteProjectV2Item(input:{projectId:$project,itemId:$item}) { deletedItemId }
        }
        """
        data = self.client.execute(query, {"project": self.project.node_id, "item": existing["item_id"]})
        return {"key": key, "deleted_item_id": (data.get("deleteProjectV2Item") or {}).get("deletedItemId")}

    def query(self, filters: dict[str, Any]) -> dict[str, Any]:
        include_archived = bool(filters.get("include_archived", False))
        max_scan = int(filters.get("max_scan", 5000))
        records, truncated = self.memory_items(include_archived=include_archived, max_items=max_scan)
        text = str(filters.get("text", "")).casefold().strip()
        kind = filters.get("kind")
        standing = filters.get("standing")
        cell = filters.get("cell")
        tags = set(str(tag) for tag in (filters.get("tags") or []))
        match_all_tags = bool(filters.get("match_all_tags", True))

        def include(record: dict[str, Any]) -> bool:
            meta = record.get("metadata") or {}
            if kind is not None and meta.get("kind") != kind:
                return False
            if standing is not None and meta.get("standing") != standing:
                return False
            if cell is not None and meta.get("cell") != cell:
                return False
            record_tags = set(str(tag) for tag in (meta.get("tags") or []))
            if tags and (not (tags <= record_tags) if match_all_tags else not bool(tags & record_tags)):
                return False
            if text:
                haystack = "\n".join([record.get("title", ""), record.get("body", ""), json_dumps(meta)]).casefold()
                if text not in haystack:
                    return False
            return True

        matched = [record for record in records if include(record)]
        matched.sort(key=lambda r: str((r.get("metadata") or {}).get("updated_at", "")), reverse=True)
        limit = max(1, min(int(filters.get("limit", 50)), 500))
        return {"records": matched[:limit], "matched": len(matched), "scanned": len(records), "truncated": truncated or len(matched) > limit}

    def snapshot(self, *, max_items: int = 500) -> dict[str, Any]:
        items, truncated = self.list_items(max_items=max_items)
        memory_count = 0
        summarized: list[dict[str, Any]] = []
        for item in items:
            content = item.get("content") or {}
            meta, _ = decode_memory_body(content.get("body") or "")
            if meta:
                memory_count += 1
            summarized.append(
                {
                    "item_id": item.get("id"),
                    "content_id": content.get("id"),
                    "type": item.get("type"),
                    "is_archived": bool(item.get("isArchived")),
                    "title": content.get("title"),
                    "memory_key": meta.get("key") if meta else None,
                    "memory_kind": meta.get("kind") if meta else None,
                    "memory_updated_at": meta.get("updated_at") if meta else None,
                }
            )
        return {
            "project": {"owner": self.project.owner, "number": self.project.number, "id": self.project.node_id, "title": self.project.title, "url": self.project.url},
            "items": summarized,
            "item_count": len(summarized),
            "memory_item_count": memory_count,
            "truncated": truncated,
        }

    @staticmethod
    def _record_from_mutation(item: dict[str, Any]) -> dict[str, Any]:
        content = item.get("content") or {}
        metadata, body = decode_memory_body(content.get("body") or "")
        return {
            "item_id": item.get("id"),
            "content_id": content.get("id"),
            "title": content.get("title") or "",
            "body": body,
            "is_archived": False,
            "metadata": metadata or {},
        }


def require_key(record: dict[str, Any]) -> str:
    key = str(record.get("key", "")).strip()
    if not key:
        raise ProxyError("memory record requires non-empty key", standing="REFUSED", reason="INVALID_REQUEST")
    if len(key) > 240:
        raise ProxyError("memory key exceeds 240 characters", standing="REFUSED", reason="INVALID_REQUEST")
    return key


def normalize_record(record: dict[str, Any], existing: dict[str, Any] | None) -> tuple[str, str, dict[str, Any]]:
    key = require_key(record)
    existing_meta = dict((existing or {}).get("metadata") or {})
    metadata = existing_meta
    metadata.update(dict(record.get("metadata") or {}))
    for field in ("kind", "standing", "cell", "generation", "repo", "ref", "head_sha", "provenance", "authority", "expires_at"):
        if field in record:
            metadata[field] = record[field]
    if "tags" in record:
        metadata["tags"] = sorted(set(str(tag) for tag in (record.get("tags") or [])))
    metadata["key"] = key
    metadata.setdefault("created_at", existing_meta.get("created_at") or utc_now())
    metadata["updated_at"] = utc_now()
    metadata["schema"] = "chatgpt-project-memory/v1"
    title = str(record.get("title") or (existing or {}).get("title") or key).strip()
    if not title:
        title = key
    body = str(record.get("body") if "body" in record else (existing or {}).get("body") or "")
    return title[:1024], body, metadata


def validate_request(request: dict[str, Any], allowed_owner: str, allowed_number: int) -> tuple[str, str]:
    request_id = str(request.get("request_id", "")).strip()
    if not request_id:
        raise ProxyError("request_id is required", standing="REFUSED", reason="INVALID_REQUEST")
    operation = str(request.get("operation", "")).strip()
    if operation not in ALLOWED_OPERATIONS:
        raise ProxyError(f"operation not allowed: {operation}", standing="REFUSED", reason="INVALID_OPERATION")
    project = request.get("project") or {}
    owner = str(project.get("owner", allowed_owner))
    number = int(project.get("number", allowed_number))
    if owner != allowed_owner or number != allowed_number:
        raise ProxyError(
            f"request targets non-admitted project {owner}/{number}", standing="REFUSED", reason="PROJECT_SCOPE_VIOLATION"
        )
    return request_id, operation


def execute_request(store: ProjectMemoryStore, request: dict[str, Any], operation: str) -> Any:
    payload = request.get("payload") or {}
    if operation == "project.snapshot":
        return store.snapshot(max_items=int(payload.get("max_items", 500)))
    if operation == "project.items":
        items, truncated = store.project_items(
            types=payload.get("types"),
            include_archived=bool(payload.get("include_archived", False)),
            max_items=int(payload.get("max_items", 5000)),
        )
        return {"items": items, "item_count": len(items), "truncated": truncated}
    if operation == "memory.create":
        return store.create(payload.get("record") or payload)
    if operation == "memory.read":
        key = str(payload.get("key", "")).strip()
        if not key:
            raise ProxyError("memory.read requires key", standing="REFUSED", reason="INVALID_REQUEST")
        record = store.find_by_key(key, include_archived=bool(payload.get("include_archived", True)))
        if not record:
            raise ProxyError(f"Memory key not found: {key}", standing="REFUSED", reason="MEMORY_NOT_FOUND")
        return record
    if operation == "memory.update":
        key = str(payload.get("key", "")).strip()
        return store.update(key, payload.get("record") or payload)
    if operation == "memory.upsert":
        action, record = store.upsert(payload.get("record") or payload)
        return {"action": action, "record": record}
    if operation == "memory.query":
        return store.query(payload)
    if operation == "memory.archive":
        return store.archive(str(payload.get("key", "")).strip())
    if operation == "memory.delete":
        return store.delete(str(payload.get("key", "")).strip())
    raise AssertionError(operation)


def receipt_for(request_path: Path, request: dict[str, Any], request_id: str | None, operation: str | None, token_source: str) -> dict[str, Any]:
    return {
        "schema": "chatgpt-project-memory-receipt/v1",
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
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)

    allowed_owner = os.environ.get("PROJECT_MEMORY_OWNER", "seanchatmangpt")
    allowed_number = int(os.environ.get("PROJECT_MEMORY_NUMBER", "2"))
    token_source = os.environ.get("PROJECTS_TOKEN_SOURCE", "unknown")
    request: dict[str, Any] = {}
    request_id: str | None = None
    operation: str | None = None

    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        request_id, operation = validate_request(request, allowed_owner, allowed_number)
        receipt = receipt_for(args.request, request, request_id, operation, token_source)
        client = GraphQLClient(os.environ.get("PROJECTS_TOKEN", ""), token_source=token_source)
        store = ProjectMemoryStore(client, allowed_owner, allowed_number)
        result = execute_request(store, request, operation)
        receipt.update(
            {
                "standing": "ALIVE",
                "reason": None,
                "result": result,
                "project": {"owner": store.project.owner, "number": store.project.number, "id": store.project.node_id, "title": store.project.title, "url": store.project.url},
            }
        )
        exit_code = 0
    except ProxyError as exc:
        receipt = receipt_for(args.request, request, request_id, operation, token_source)
        receipt.update(
            {
                "standing": exc.standing,
                "reason": exc.reason,
                "error": {"type": type(exc).__name__, "message": str(exc), "details": exc.details},
            }
        )
        exit_code = 3 if exc.standing == "BLOCKED" else 2 if exc.standing == "REFUSED" else 1
    except Exception as exc:
        receipt = receipt_for(args.request, request, request_id, operation, token_source)
        receipt.update(
            {
                "standing": "BUILD_BROKEN",
                "reason": "UNHANDLED_PROXY_FAILURE",
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
        )
        exit_code = 1

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"request_id": receipt.get("request_id"), "operation": receipt.get("operation"), "standing": receipt.get("standing"), "reason": receipt.get("reason")}, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
