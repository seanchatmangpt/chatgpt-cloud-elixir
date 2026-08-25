#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "versions.toml"
CONTROL_PLANE = ROOT / "control-plane" / "mix.exs"


def fail(message: str) -> None:
    print(f"BUILD_BROKEN: {message}", file=sys.stderr)
    raise SystemExit(65)


with VERSIONS.open("rb") as handle:
    versions = tomllib.load(handle)

release = versions.get("release", {})
version = release.get("version")
release_date = release.get("date")

if not isinstance(version, str) or not re.fullmatch(r"\d{2}\.\d{1,2}\.\d{1,2}", version):
    fail("release.version must be YY.M.D CalVer")

if not isinstance(release_date, str):
    fail("release.date must be an ISO-8601 date string")

try:
    yy, month, day = (int(part) for part in version.split("."))
    expected_date = dt.date(2000 + yy, month, day).isoformat()
except ValueError as exc:
    fail(f"release.version is not a real calendar date: {exc}")

if release_date != expected_date:
    fail(f"release.date={release_date} does not match CalVer date {expected_date}")

mix_body = CONTROL_PLANE.read_text()
match = re.search(r'\bversion:\s*"([^"]+)"', mix_body)
if not match:
    fail("control-plane/mix.exs does not declare a project version")

control_plane_version = match.group(1)
if control_plane_version != version:
    fail(
        "control-plane version drift: "
        f"versions.toml={version} control-plane/mix.exs={control_plane_version}"
    )

print(
    json.dumps(
        {
            "schema_version": 1,
            "check": "release_identity",
            "release_version": version,
            "release_date": release_date,
            "control_plane_version": control_plane_version,
            "standing": "ALIVE",
        },
        sort_keys=True,
    )
)
