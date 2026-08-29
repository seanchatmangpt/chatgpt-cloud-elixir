defmodule ChatGPTCloud.RuntimeIntegration.ProducerSpoolTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.ProducerSpool

  test "spool identity binds producer subject without altering standing" do
    spool = ProducerSpool.new("ex4pm", "event-1", :partial_alive)
    assert spool.producer == "ex4pm"
    assert spool.event_id == "event-1"
    assert spool.subject_standing == :partial_alive
    refute ProducerSpool.may_upgrade_standing?(spool)
  end
end
