defmodule ChatGPTCloud.DataCase do
  use ExUnit.CaseTemplate

  using do
    quote do
      alias ChatGPTCloud.Repo
    end
  end

  setup tags do
    pid = Ecto.Adapters.SQL.Sandbox.start_owner!(ChatGPTCloud.Repo, shared: not tags[:async])
    on_exit(fn -> Ecto.Adapters.SQL.Sandbox.stop_owner(pid) end)
    :ok
  end
end
