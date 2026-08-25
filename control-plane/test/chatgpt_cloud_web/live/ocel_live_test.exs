defmodule ChatGPTCloudWeb.OcelLiveTest do
  use ChatGPTCloudWeb.ConnCase, async: false

  test "renders live process intelligence surface", %{conn: conn} do
    {:ok, _view, html} = live(conn, "/process-intelligence/live")
    assert html =~ "Streaming OCEL Process Intelligence"
    assert html =~ "AshAdmin"
  end
end
