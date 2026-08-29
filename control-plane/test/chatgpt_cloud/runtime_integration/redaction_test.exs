defmodule ChatGPTCloud.RuntimeIntegration.RedactionTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.Redaction

  test "redacts atom and string secret keys without changing ordinary evidence" do
    assert %{:token => "[REDACTED]", "PASSWORD" => "[REDACTED]", exit_code: 0} =
             Redaction.apply(%{:token => "abc", "PASSWORD" => "def", exit_code: 0})
  end
end
