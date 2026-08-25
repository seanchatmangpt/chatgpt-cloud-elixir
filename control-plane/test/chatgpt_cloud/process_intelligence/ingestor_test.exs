defmodule ChatGPTCloud.ProcessIntelligence.IngestorTest do
  use ChatGPTCloud.DataCase, async: false

  alias ChatGPTCloud.ProcessIntelligence.Ingestor

  test "ingests one OCEL world idempotently" do
    envelope = %{
      "schema" => "chatgpt-cloud-ocel/1",
      "producer" => %{
        "agent_id" => "chatgpt-agent-1",
        "run_id" => "run-1",
        "status" => "running",
        "subject_repo" => "seanchatmangpt/ash_r2rml",
        "subject_sha" => String.duplicate("a", 40)
      },
      "events" => [
        %{
          "id" => "event-1",
          "activity" => "github.commit",
          "lifecycle" => "complete",
          "sequence" => 1,
          "standing" => "ALIVE",
          "authority_domain" => "CONSTRUCT",
          "timestamp" => "2026-08-22T00:00:00.000000Z",
          "objects" => [
            %{"id" => "repo:ash_r2rml", "type" => "Repository", "qualifier" => "target"}
          ],
          "payload" => %{"commit_sha" => String.duplicate("a", 40)}
        }
      ],
      "receipts" => [
        %{
          "id" => "receipt-1",
          "standing" => "ALIVE",
          "subject_sha" => String.duplicate("a", 40),
          "payload" => %{"tests" => 51, "failures" => 0}
        }
      ]
    }

    assert {:ok, %{accepted_events: 1, duplicate_events: 0, standing: "ALIVE"}} =
             Ingestor.ingest(envelope)

    assert {:ok, %{accepted_events: 0, duplicate_events: 1}} = Ingestor.ingest(envelope)

    assert %{rows: [[1]]} =
             Ecto.Adapters.SQL.query!(Repo, "SELECT count(*)::bigint FROM ocel_events", [])

    assert %{rows: [[1]]} =
             Ecto.Adapters.SQL.query!(Repo, "SELECT count(*)::bigint FROM ocel_receipts", [])

    assert %{rows: [["target"]]} =
             Ecto.Adapters.SQL.query!(Repo, "SELECT qualifier FROM ocel_event_objects", [])
  end

  test "refuses unknown standing rather than silently coercing it" do
    envelope = %{
      "schema" => "chatgpt-cloud-ocel/1",
      "producer" => %{"agent_id" => "a", "run_id" => "r"},
      "events" => [
        %{
          "activity" => "x",
          "sequence" => 1,
          "standing" => "GOOD",
          "timestamp" => "2026-08-22T00:00:00Z"
        }
      ]
    }

    assert {:error, :invalid_standing} = Ingestor.ingest(envelope)
  end
end
