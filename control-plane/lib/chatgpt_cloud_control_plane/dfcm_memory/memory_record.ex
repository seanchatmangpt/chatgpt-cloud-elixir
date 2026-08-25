defmodule ChatGPTCloud.DfcmMemory.MemoryRecord do
  @moduledoc """
  Ash wrapper over GitHub Project v2 `seanchatmangpt/2`, following the
  "wrap external APIs as an Ash resource" pattern
  (https://ash.hexdocs.pm/wrap-external-apis.html): attributes matching the
  external shape, a manual `:read` action that calls the API and applies the
  query, generic actions for the write operations the wrapped API supports.

  This resource is not backed by `ChatGPTCloud.Repo` or any local store — every
  action is a live call to GitHub. It is the read/query/upsert half of the same
  memory `project-memory/README.md` documents; the other half is
  `scripts/project_memory_proxy.py` run from `.github/workflows/project-memory-proxy.yml`.
  Both write the same body-encoded records to the same Project, so either side can
  read what the other wrote.
  """

  use Ash.Resource,
    otp_app: :chatgpt_cloud_control_plane,
    domain: ChatGPTCloud.DfcmMemory,
    data_layer: Ash.DataLayer.Simple

  attributes do
    attribute :key, :string, primary_key?: true, allow_nil?: false, public?: true
    attribute :title, :string, public?: true
    attribute :kind, :string, public?: true
    attribute :cell, :string, public?: true
    attribute :standing, :string, public?: true
    attribute :tags, {:array, :string}, public?: true, default: []
    attribute :body, :string, public?: true
    attribute :metadata, :map, public?: true, default: %{}
    attribute :item_id, :string, public?: true
    attribute :content_id, :string, public?: true
    attribute :is_archived, :boolean, public?: true, default: false
    attribute :updated_at, :string, public?: true
  end

  actions do
    read :read do
      primary? true
      manual ChatGPTCloud.DfcmMemory.ManualRead
    end

    action :upsert_record, :map do
      description """
      Read-before-manufacture, write-after-manufacture entry point for the DfCM
      loop (see project-memory/README.md). Creates the memory record for `key`
      if it does not exist, updates it in place if it does. Every call goes
      against the live, hard-scoped Project seanchatmangpt/2 — there is no local
      cache to go stale.
      """

      argument :key, :string, allow_nil?: false
      argument :title, :string
      argument :kind, :string
      argument :cell, :string
      argument :standing, :string
      argument :tags, {:array, :string}, default: []
      argument :body, :string, default: ""
      argument :metadata, :map, default: %{}

      run ChatGPTCloud.DfcmMemory.UpsertRecord
    end

    action :snapshot, :map do
      description "Live Project #2 identity + item/memory-record counts. Read-only, no mutation."
      run ChatGPTCloud.DfcmMemory.Snapshot
    end

    action :project_items, {:array, :map} do
      description """
      Full-fidelity read of every item on Project #2 (seanchatmangpt/2) -- not just
      memory-marked ones. Returns id/type/archived state, content (title, body, url,
      number, repository, state, labels, assignees), and every custom field value
      flattened to a plain {field_name => value} map. Read-only, no mutation.
      """

      argument :max_items, :integer
      argument :types, {:array, :string}
      argument :include_archived, :boolean, default: false

      run ChatGPTCloud.DfcmMemory.ProjectItems
    end
  end
end
