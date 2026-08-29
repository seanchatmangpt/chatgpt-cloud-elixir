defmodule ChatGPTCloud.RuntimeIntegration.QualificationCommandTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.QualificationCommand

  test "qualification command must name executable command and exact scope" do
    assert {:ok, command} = QualificationCommand.new("mix test", :runtime)
    assert command.command == "mix test"
    assert command.scope == :runtime
    assert {:error, :qualification_command_required} = QualificationCommand.new("", :runtime)
  end
end
