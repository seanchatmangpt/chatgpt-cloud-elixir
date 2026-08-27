defmodule ChatGPTCloud.RuntimeIntegration.ServiceCandidateTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ServiceCandidate

  test "candidate requires service endpoint and observed availability" do
    assert ServiceCandidate.admitted?(%ServiceCandidate{name: :postgres, endpoint: "postgres://db", observed: true})
    refute ServiceCandidate.admitted?(%ServiceCandidate{name: :postgres, endpoint: nil, observed: true})
    refute ServiceCandidate.admitted?(%ServiceCandidate{name: :postgres, endpoint: "postgres://db", observed: false})
  end
end
