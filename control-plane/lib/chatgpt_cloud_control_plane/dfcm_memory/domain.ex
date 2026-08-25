defmodule ChatGPTCloud.DfcmMemory do
  @moduledoc """
  The Claude <-> ChatGPT junction over DfCM shared memory.

  ChatGPT's five hourly manufacturing cells (MEASURE/EXPLORE/SELECT/IMPLEMENT/
  PORTFOLIO) write to GitHub Project v2 `seanchatmangpt/2` through
  `scripts/project_memory_proxy.py` + `.github/workflows/project-memory-proxy.yml`.
  This domain exposes the same Project, hard-scoped the same way, to Claude (or
  any MCP client) as Ash tools over `/mcp` — so both sides read and write one
  shared, evidence-bearing memory rather than two private ones.

  Per `project-memory/README.md`'s read-before-manufacture / write-after-
  manufacture contract: reading here is a required first step before any
  manufacturing decision, and every write is an upsert bound to a stable `key`,
  never a blind create.
  """

  use Ash.Domain, extensions: [AshAi]

  tools do
    tool :read_dfcm_memory, ChatGPTCloud.DfcmMemory.MemoryRecord, :read,
      description:
        "Read-before-manufacture: list current DfCM memory records from Project #2 " <>
          "(seanchatmangpt/2). Filter by key/kind/cell/standing/tags via the Ash query " <>
          "(pass filter conditions under \"filter\", arguments under \"input\"). Call this " <>
          "before proposing or starting any manufacturing work."

    tool :upsert_dfcm_memory, ChatGPTCloud.DfcmMemory.MemoryRecord, :upsert_record,
      description:
        "Write-after-manufacture: create-or-update a DfCM memory record by stable key " <>
          "(e.g. dfcm/frontier/current, dfcm/measure/latest; pass key/title/kind/cell/" <>
          "standing/tags/body/metadata under \"input\"). Always resolves the current record " <>
          "for that key first, so this is an upsert, never a blind overwrite. Call this after " <>
          "every manufacturing run, including runs that produced no new commits."

    tool :snapshot_dfcm_project, ChatGPTCloud.DfcmMemory.MemoryRecord, :snapshot,
      description:
        "Live identity and item/memory-record counts for Project #2 (seanchatmangpt/2). " <>
          "Read-only. Useful for confirming the junction is actually connected before " <>
          "trusting any cached memory read."
  end

  resources do
    resource ChatGPTCloud.DfcmMemory.MemoryRecord
  end
end
