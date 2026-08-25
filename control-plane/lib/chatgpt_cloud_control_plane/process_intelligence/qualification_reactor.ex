defmodule ChatGPTCloud.ProcessIntelligence.QualificationReactor do
  @moduledoc "Reactor saga that turns one admitted receipt into one bounded qualification decision."

  use Ash.Reactor

  alias ChatGPTCloud.ProcessIntelligence.Qualification

  ash do
    default_domain ChatGPTCloud.ProcessIntelligence
  end

  input(:qualification)
  input(:receipt)

  update :start_qualification, Qualification, :start do
    initial input(:qualification)
    async? false
  end

  step :admit_receipt do
    argument :qualification, result(:start_qualification)
    argument :receipt, input(:receipt)
    async? false

    run fn %{qualification: qualification, receipt: receipt}, _context ->
      ChatGPTCloud.ProcessIntelligence.QualificationReconciler.finish(qualification, receipt)
    end
  end

  return :admit_receipt
end

defmodule ChatGPTCloud.ProcessIntelligence.QualificationReconciler do
  @moduledoc "Deterministically reconciles pending qualifications against persisted receipt evidence."

  alias ChatGPTCloud.ProcessIntelligence.{Qualification, QualificationReactor, Receipt}

  @terminal_states [:qualified, :degraded, :blocked, :failed]

  def reconcile_pending do
    Qualification
    |> Ash.read!()
    |> Enum.reject(&(&1.state in @terminal_states or &1.state == :running))
    |> Enum.reduce(0, fn qualification, count ->
      case newest_receipt(qualification.run_key) do
        nil ->
          count

        receipt ->
          case Reactor.run(
                 QualificationReactor,
                 %{qualification: qualification, receipt: receipt},
                 %{},
                 async?: false
               ) do
            {:ok, _} -> count + 1
            {:ok, _, _} -> count + 1
            {:error, _} -> count
            {:halted, _} -> count
          end
      end
    end)
  end

  def finish(qualification, receipt) do
    {action, standing} = decision(receipt.standing)

    result = %{
      "receipt_key" => receipt.receipt_key,
      "receipt_digest" => receipt.digest,
      "subject_sha" => receipt.subject_sha,
      "subject_tree_sha" => receipt.subject_tree_sha,
      "observed_at" => DateTime.to_iso8601(receipt.observed_at)
    }

    qualification
    |> Ash.Changeset.for_update(action, %{standing: standing, result: result})
    |> Ash.update()
  end

  defp newest_receipt(run_key) do
    Receipt
    |> Ash.read!()
    |> Enum.filter(&(&1.run_key == run_key))
    |> Enum.sort_by(&DateTime.to_unix(&1.observed_at, :microsecond), :desc)
    |> List.first()
  end

  defp decision("ALIVE"), do: {:qualify, "ALIVE"}
  defp decision("PARTIAL_ALIVE"), do: {:degrade, "PARTIAL_ALIVE"}
  defp decision("BUILD_BROKEN"), do: {:fail, "BUILD_BROKEN"}
  defp decision("BLOCKED"), do: {:block, "BLOCKED"}
  defp decision("UNSUPPORTED"), do: {:block, "UNSUPPORTED"}
  defp decision(_), do: {:block, "UNKNOWN"}
end
