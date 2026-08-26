defmodule ChatGPTCloud.SwarmCoordination.Project2 do
  @moduledoc """
  Project #2 -> SwarmSH work-envelope adapter.

  Project items supply demand. They do not schedule or actuate work. Import is
  idempotent because every Project item is assigned a deterministic work id.
  """

  alias ChatGPTCloud.DfcmMemory.GithubProjectClient
  alias ChatGPTCloud.SwarmCoordination.Coordinator

  def import(opts \\ []) do
    max_items = Keyword.get(opts, :max_items, 500)
    include_archived = Keyword.get(opts, :include_archived, false)
    types = Keyword.get(opts, :types, ["ISSUE", "PULL_REQUEST", "DRAFT_ISSUE"])

    with {:ok, items} <-
           GithubProjectClient.project_items(
             max_items: max_items,
             include_archived: include_archived,
             types: types
           ) do
      results = Enum.map(items, &import_item/1)

      {:ok,
       %{
         "schema" => "swarmsh.project2-import/v1",
         "project" => %{"owner" => "seanchatmangpt", "number" => 2},
         "observed_items" => length(items),
         "accepted" => Enum.count(results, &match?({:ok, _, _}, &1)),
         "results" => Enum.map(results, &result_json/1)
       }}
    end
  end

  def import_item(item) when is_map(item) do
    Coordinator.enqueue(project_item_to_work(item))
  end

  def project_item_to_work(item) when is_map(item) do
    item_id = value(item, :item_id) || value(item, :content_id) || value(item, :url) || "unknown"
    fields = value(item, :field_values, %{}) || %{}
    title = value(item, :title, "")
    body = value(item, :body, "")

    %{
      work_item_id: deterministic_work_id(item_id),
      source_kind: "github_project_v2",
      source_id: item_id,
      work_type: item |> value(:type, "work") |> to_string() |> String.downcase(),
      description: if(body in [nil, ""], do: title, else: body),
      priority: project_field(fields, "Priority", "medium") |> normalize_priority(),
      team: project_field(fields, "Team", "chatgpt_swarm") |> to_string(),
      subject: %{
        "repository" => value(item, :repository),
        "url" => value(item, :url),
        "number" => value(item, :number),
        "state" => value(item, :state),
        "title" => title
      },
      metadata: %{
        "project_item_type" => value(item, :type),
        "labels" => value(item, :labels, []),
        "assignees" => value(item, :assignees, []),
        "field_values" => fields,
        "is_archived" => value(item, :is_archived, false)
      }
    }
  end

  defp deterministic_work_id(source_id) do
    suffix =
      source_id
      |> to_string()
      |> then(&:crypto.hash(:sha256, &1))
      |> Base.encode16(case: :lower)
      |> binary_part(0, 24)

    "project2_#{suffix}"
  end

  defp project_field(fields, name, default) do
    Map.get(fields, name, Map.get(fields, String.to_atom(name), default)) || default
  end

  defp normalize_priority(value) do
    case value |> to_string() |> String.downcase() do
      value when value in ["critical", "urgent", "p0"] -> "critical"
      value when value in ["high", "p1"] -> "high"
      value when value in ["low", "p3", "p4"] -> "low"
      _ -> "medium"
    end
  end

  defp result_json({:ok, work, receipt}), do: %{"work" => work, "receipt" => receipt}
  defp result_json({:error, reason}), do: %{"error" => inspect(reason)}

  defp value(map, key, default \\ nil) do
    Map.get(map, key, Map.get(map, Atom.to_string(key), default))
  end
end
