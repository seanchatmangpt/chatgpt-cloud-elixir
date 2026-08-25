defmodule ChatGPTCloud.DfcmMemory.GithubProjectClient do
  @moduledoc """
  Bounded GitHub Project v2 GraphQL client for `seanchatmangpt/2`.

  This is the Claude-side (control-plane / MCP) half of the same junction the
  ChatGPT-side scheduled cells write through via `scripts/project_memory_proxy.py`
  and `.github/workflows/project-memory-proxy.yml`. Both halves target the same
  Project, the same hard-scoped owner/number, and the same memory-record body
  encoding, so a record either side writes is legible to the other.

  Hard-scoped, deliberately, to mirror `project-memory/README.md`'s "Authority"
  section:

    - owner: `seanchatmangpt` (`config :chatgpt_cloud_control_plane, :dfcm_memory, owner: ...`)
    - project number: `2` (`config :chatgpt_cloud_control_plane, :dfcm_memory, number: ...`)

  These are read from application config (see `config/config.exs`), not
  compiled-in literals, so a deployment can point at a different owner/project
  without editing source — the same shape as `scripts/project_memory_proxy.py`'s
  `allowed_owner`/`allowed_number` init params. The default (`seanchatmangpt`/
  `2`) matches the Python proxy's hard-coded scope so the two transports agree
  unless someone deliberately reconfigures both; nothing a remote GraphQL
  caller sends can change these values at runtime — they come only from this
  process's own compiled config, never from request/response data.

  Not general-purpose GraphQL. Raw queries are not accepted from callers.
  """

  @default_owner "seanchatmangpt"
  @default_number 2
  @api_url "https://api.github.com/graphql"
  @marker_prefix "<!-- chatgpt-project-memory:v1 "
  @marker_re ~r/^<!-- chatgpt-project-memory:v1 ([A-Za-z0-9_-]+) -->\n?/m
  @default_list_max_items 5000
  @default_snapshot_max_items 500
  @request_timeout_ms 30_000

  defp allowed_owner do
    :chatgpt_cloud_control_plane
    |> Application.get_env(:dfcm_memory, [])
    |> Keyword.get(:owner, @default_owner)
  end

  defp allowed_number do
    :chatgpt_cloud_control_plane
    |> Application.get_env(:dfcm_memory, [])
    |> Keyword.get(:number, @default_number)
  end

  defmodule ProxyError do
    defexception [:message, standing: "UNKNOWN", reason: nil, details: nil]
  end

  @doc "Resolve the auth token the same way the Python proxy does: PROJECTS_TOKEN > GH_TOKEN > GH_PAT > GITHUB_PAT > GITHUB_TOKEN."
  def resolve_token do
    Enum.find_value(
      ["PROJECTS_TOKEN", "GH_TOKEN", "GH_PAT", "GITHUB_PAT", "GITHUB_TOKEN"],
      fn name ->
        case System.get_env(name) do
          nil -> nil
          "" -> nil
          value -> {value, name}
        end
      end
    )
  end

  @doc "Resolve the configured Project's node id, title, and url."
  def resolve_project do
    query = """
    query($login: String!, $number: Int!) {
      user(login: $login) {
        projectV2(number: $number) { id title url }
      }
    }
    """

    owner = allowed_owner()
    number = allowed_number()

    with {:ok, data} <- execute(query, %{login: owner, number: number}) do
      case get_in(data, ["user", "projectV2"]) do
        nil ->
          {:error,
           %ProxyError{
             message: "Configured project was not visible",
             standing: "BLOCKED",
             reason: "IRREDUCIBLE_AUTHORITY"
           }}

        project ->
          {:ok,
           %{
             owner: owner,
             number: number,
             id: project["id"],
             title: project["title"] || "",
             url: project["url"] || ""
           }}
      end
    end
  end

  @doc "List every item (draft issue, issue, PR) currently on the Project, paginated."
  def list_items(max_items \\ @default_list_max_items) do
    with {:ok, project} <- resolve_project() do
      query = """
      query($project: ID!, $after: String) {
        node(id: $project) {
          ... on ProjectV2 {
            items(first: 100, after: $after) {
              nodes {
                id
                isArchived
                type
                content {
                  ... on DraftIssue { id title body }
                  ... on Issue {
                    id title body url number state
                    repository { nameWithOwner }
                    labels(first: 20) { nodes { name color } }
                    assignees(first: 10) { nodes { login } }
                  }
                  ... on PullRequest {
                    id title body url number state
                    repository { nameWithOwner }
                    labels(first: 20) { nodes { name color } }
                    assignees(first: 10) { nodes { login } }
                  }
                }
                fieldValues(first: 20) {
                  nodes {
                    ... on ProjectV2ItemFieldTextValue {
                      text
                      field { ... on ProjectV2FieldCommon { name } }
                    }
                    ... on ProjectV2ItemFieldNumberValue {
                      number
                      field { ... on ProjectV2FieldCommon { name } }
                    }
                    ... on ProjectV2ItemFieldDateValue {
                      date
                      field { ... on ProjectV2FieldCommon { name } }
                    }
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                      field { ... on ProjectV2FieldCommon { name } }
                    }
                    ... on ProjectV2ItemFieldIterationValue {
                      title
                      startDate
                      duration
                      field { ... on ProjectV2FieldCommon { name } }
                    }
                  }
                }
              }
              pageInfo { hasNextPage endCursor }
            }
          }
        }
      }
      """

      collect_pages(query, %{"project" => project.id}, [], max_items)
    end
  end

  @default_project_items_max_items 5000

  @doc """
  Full-fidelity item listing: id/type/archived state, content (title, body,
  url, number, repository, state, labels, assignees), and every custom field
  value on the item flattened to a plain `%{field_name => value}` map — not the
  raw GraphQL `ProjectV2ItemFieldValue` union. Mirrors the Python proxy's
  `project.items` operation. Read-only; supports the same `types`/
  `include_archived` client-side filters (GraphQL `items()` takes no server-side
  filter beyond pagination).
  """
  def project_items(opts \\ []) do
    max_items = Keyword.get(opts, :max_items, @default_project_items_max_items)
    types = opts |> Keyword.get(:types) |> normalize_types()
    include_archived = Keyword.get(opts, :include_archived, false)

    with {:ok, {items, _truncated}} <- list_items(max_items) do
      mapped =
        items
        |> Enum.filter(fn item -> include_archived or not item["isArchived"] end)
        |> Enum.filter(fn item -> is_nil(types) or item["type"] in types end)
        |> Enum.map(&map_project_item/1)

      {:ok, mapped}
    end
  end

  defp normalize_types(nil), do: nil
  defp normalize_types([]), do: nil

  defp normalize_types(types) do
    Enum.map(types, &to_string/1)
  end

  defp map_project_item(item) do
    content = item["content"] || %{}

    %{
      item_id: item["id"],
      type: item["type"],
      is_archived: !!item["isArchived"],
      content_id: content["id"],
      title: content["title"] || "",
      body: content["body"] || "",
      url: content["url"],
      number: content["number"],
      repository: get_in(content, ["repository", "nameWithOwner"]),
      state: content["state"],
      labels: map_labels(content["labels"]),
      assignees: map_assignees(content["assignees"]),
      field_values: map_field_values(item["fieldValues"])
    }
  end

  defp map_labels(nil), do: []

  defp map_labels(%{"nodes" => nodes}) do
    Enum.map(nodes || [], fn n -> %{name: n["name"], color: n["color"]} end)
  end

  defp map_assignees(nil), do: []

  defp map_assignees(%{"nodes" => nodes}) do
    Enum.map(nodes || [], fn n -> %{login: n["login"]} end)
  end

  defp map_field_values(nil), do: %{}

  defp map_field_values(%{"nodes" => nodes}) do
    nodes
    |> Enum.reduce(%{}, fn node, acc ->
      case get_in(node, ["field", "name"]) do
        nil ->
          acc

        field_name ->
          Map.put(acc, field_name, decode_field_value(node))
      end
    end)
  end

  defp decode_field_value(%{"text" => text}) when not is_nil(text), do: text
  defp decode_field_value(%{"number" => number}) when not is_nil(number), do: number
  defp decode_field_value(%{"date" => date}) when not is_nil(date), do: date
  defp decode_field_value(%{"name" => name}) when not is_nil(name), do: name

  defp decode_field_value(%{"title" => title, "startDate" => start_date, "duration" => duration})
       when not is_nil(title) do
    %{title: title, start_date: start_date, duration: duration}
  end

  defp decode_field_value(_other), do: nil

  @doc "List only items carrying the memory-record marker, decoded to {key, title, body, metadata, item_id, content_id, is_archived}."
  def memory_items(include_archived \\ false, max_items \\ @default_list_max_items) do
    with {:ok, {items, truncated}} <- list_items(max_items) do
      records =
        items
        |> Enum.filter(fn item -> include_archived or not item["isArchived"] end)
        |> Enum.flat_map(fn item ->
          content = item["content"] || %{}

          case decode_body(content["body"] || "") do
            {nil, _} ->
              []

            {metadata, text} ->
              [
                %{
                  item_id: item["id"],
                  content_id: content["id"],
                  title: content["title"] || "",
                  body: text,
                  is_archived: !!item["isArchived"],
                  metadata: metadata
                }
              ]
          end
        end)

      {:ok, {records, truncated}}
    end
  end

  @doc "Find the current memory record for a stable key, most-recently-updated wins."
  def find_by_key(key, include_archived \\ true) do
    with {:ok, {records, _truncated}} <- memory_items(include_archived) do
      match =
        records
        |> Enum.filter(fn r -> get_in(r, [:metadata, "key"]) == key end)
        |> Enum.sort_by(fn r -> to_string(get_in(r, [:metadata, "updated_at"]) || "") end, :desc)
        |> List.first()

      {:ok, match}
    end
  end

  @doc """
  Create-or-update a memory record by key (upsert). `record` must include a "key"
  string; other fields (title, kind, cell, standing, tags, body, metadata) follow
  the same shape `project-memory/README.md`'s request schema documents.
  """
  def upsert(record) do
    key = Map.get(record, "key") || Map.get(record, :key)

    if is_nil(key) or key == "" do
      {:error,
       %ProxyError{message: "record.key is required", standing: "REFUSED", reason: "MISSING_KEY"}}
    else
      with {:ok, project} <- resolve_project(),
           {:ok, existing} <- find_by_key(key) do
        now = DateTime.utc_now() |> DateTime.truncate(:second) |> DateTime.to_iso8601()

        metadata =
          record
          |> normalize_map()
          |> Map.drop(["key", "title", "body"])
          |> Map.put("key", key)
          |> Map.put("updated_at", now)

        title = Map.get(record, "title") || Map.get(record, :title) || key
        body = Map.get(record, "body") || Map.get(record, :body) || ""
        encoded = encode_body(metadata, body)

        if existing do
          mutation = """
          mutation($draft: ID!, $title: String!, $body: String!) {
            updateProjectV2DraftIssue(input: {draftIssueId: $draft, title: $title, body: $body}) {
              draftIssue { id title body }
            }
          }
          """

          with {:ok, data} <-
                 execute(mutation, %{
                   "draft" => existing.content_id,
                   "title" => title,
                   "body" => encoded
                 }) do
            draft = get_in(data, ["updateProjectV2DraftIssue", "draftIssue"]) || %{}

            {:ok,
             %{
               action: "updated",
               item_id: existing.item_id,
               content_id: draft["id"] || existing.content_id,
               title: draft["title"] || title,
               metadata: metadata,
               project: project
             }}
          end
        else
          mutation = """
          mutation($project: ID!, $title: String!, $body: String!) {
            addProjectV2DraftIssue(input: {projectId: $project, title: $title, body: $body}) {
              projectItem { id content { ... on DraftIssue { id title body } } }
            }
          }
          """

          with {:ok, data} <-
                 execute(mutation, %{"project" => project.id, "title" => title, "body" => encoded}) do
            item = get_in(data, ["addProjectV2DraftIssue", "projectItem"]) || %{}
            content = item["content"] || %{}

            {:ok,
             %{
               action: "created",
               item_id: item["id"],
               content_id: content["id"],
               title: content["title"] || title,
               metadata: metadata,
               project: project
             }}
          end
        end
      end
    end
  end

  @doc "Whole-project summary: identity, item count, memory-record count."
  def snapshot(max_items \\ @default_snapshot_max_items) do
    with {:ok, project} <- resolve_project(),
         {:ok, {items, truncated}} <- list_items(max_items) do
      memory_count =
        Enum.count(items, fn item ->
          {metadata, _text} = decode_body(get_in(item, ["content", "body"]) || "")
          not is_nil(metadata)
        end)

      {:ok,
       %{
         project: project,
         item_count: length(items),
         memory_item_count: memory_count,
         truncated: truncated
       }}
    end
  end

  # -- internals --------------------------------------------------------

  defp collect_pages(query, base_vars, acc, max_items, after_cursor \\ nil) do
    vars = Map.put(base_vars, "after", after_cursor)

    with {:ok, data} <- execute(query, vars) do
      conn = get_in(data, ["node", "items"]) || %{}
      nodes = conn["nodes"] || []
      acc = acc ++ Enum.filter(nodes, & &1)

      cond do
        length(acc) >= max_items ->
          {:ok, {Enum.take(acc, max_items), true}}

        get_in(conn, ["pageInfo", "hasNextPage"]) ->
          collect_pages(query, base_vars, acc, max_items, get_in(conn, ["pageInfo", "endCursor"]))

        true ->
          {:ok, {acc, false}}
      end
    end
  end

  defp execute(query, variables) do
    case resolve_token() do
      nil ->
        {:error,
         %ProxyError{
           message: "No GitHub token available",
           standing: "BLOCKED",
           reason: "IRREDUCIBLE_AUTHORITY"
         }}

      {token, _source} ->
        body = Jason.encode!(%{query: query, variables: variables})

        headers = [
          {~c"authorization", String.to_charlist("Bearer " <> token)},
          {~c"accept", ~c"application/vnd.github+json"},
          {~c"x-github-api-version", ~c"2022-11-28"},
          {~c"user-agent", ~c"chatgpt-cloud-control-plane-dfcm-mcp/1"}
        ]

        request = {String.to_charlist(@api_url), headers, ~c"application/json", body}

        case :httpc.request(:post, request, [{:timeout, @request_timeout_ms}], []) do
          {:ok, {{_line, status, _reason}, _resp_headers, resp_body}} when status in 200..299 ->
            data = Jason.decode!(resp_body)

            case data["errors"] do
              nil ->
                {:ok, data["data"] || %{}}

              [] ->
                {:ok, data["data"] || %{}}

              errors ->
                message = Enum.map_join(errors, " | ", &(&1["message"] || inspect(&1)))
                lowered = String.downcase(message)

                {standing, reason} =
                  if String.contains?(lowered, "resource not accessible") or
                       String.contains?(lowered, "forbidden") or
                       String.contains?(lowered, "permission") or
                       String.contains?(lowered, "scope") or
                       String.contains?(lowered, "could not resolve to a user") do
                    {"BLOCKED", "IRREDUCIBLE_AUTHORITY"}
                  else
                    {"UNKNOWN", "GRAPHQL_ERROR"}
                  end

                {:error,
                 %ProxyError{
                   message: message,
                   standing: standing,
                   reason: reason,
                   details: errors
                 }}
            end

          {:ok, {{_line, status, _reason}, _resp_headers, resp_body}} when status in [401, 403] ->
            {:error,
             %ProxyError{
               message: "GitHub GraphQL authorization failed with HTTP #{status}",
               standing: "BLOCKED",
               reason: "IRREDUCIBLE_AUTHORITY",
               details: %{http_status: status, body: String.slice(to_string(resp_body), 0, 1000)}
             }}

          {:ok, {{_line, status, _reason}, _resp_headers, resp_body}} ->
            {:error,
             %ProxyError{
               message: "GitHub GraphQL HTTP failure #{status}",
               standing: "UNKNOWN",
               reason: "GITHUB_API_HTTP",
               details: %{http_status: status, body: String.slice(to_string(resp_body), 0, 1000)}
             }}

          {:error, reason} ->
            {:error,
             %ProxyError{
               message: "GitHub GraphQL network failure",
               standing: "UNKNOWN",
               reason: "NETWORK",
               details: inspect(reason)
             }}
        end
    end
  end

  defp encode_body(metadata, body) do
    marker = metadata |> canonical_json() |> Base.url_encode64(padding: false)
    trimmed = String.trim_trailing(body || "")

    if trimmed == "" do
      @marker_prefix <> marker <> " -->\n"
    else
      @marker_prefix <> marker <> " -->\n\n" <> trimmed <> "\n"
    end
  end

  # Every call site already normalizes its input with `|| ""`, so `body` here
  # is always a binary -- no further `|| ""` fallback is reachable, and the
  # compiler's type checker treats one as dead code under
  # --warnings-as-errors.
  defp decode_body(body) when is_binary(body) do
    case Regex.run(@marker_re, body, return: :index) do
      nil ->
        {nil, body}

      [{start, len} | _] ->
        marker_match = Regex.run(@marker_re, body)
        [_, encoded] = marker_match

        with {:ok, json} <- Base.url_decode64(encoded, padding: false),
             {:ok, metadata} <- Jason.decode(json) do
          cleaned =
            (String.slice(body, 0, start) <> String.slice(body, start + len, String.length(body)))
            |> String.trim_leading("\n")
            |> String.trim_trailing()

          {metadata, cleaned}
        else
          _ -> {nil, body}
        end
    end
  end

  defp normalize_map(map) do
    Enum.into(map, %{}, fn {k, v} -> {to_string(k), v} end)
  end

  # Canonical (sorted-key) JSON, matching the Python proxy's
  # `json.dumps(value, sort_keys=True, separators=(",", ":"))`.
  defp canonical_json(value), do: Jason.encode!(sort_keys(value))

  defp sort_keys(map) when is_map(map) do
    map
    |> Enum.sort_by(fn {k, _v} -> to_string(k) end)
    |> Enum.map(fn {k, v} -> {k, sort_keys(v)} end)
    |> then(&(&1 |> Enum.into(%{})))
  end

  defp sort_keys(list) when is_list(list), do: Enum.map(list, &sort_keys/1)
  defp sort_keys(other), do: other
end
