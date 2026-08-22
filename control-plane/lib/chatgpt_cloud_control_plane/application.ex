defmodule ChatGPTCloud.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children = [
      ChatGPTCloud.Repo,
      ChatGPTCloud.Vault,
      {Phoenix.PubSub, name: ChatGPTCloud.PubSub},
      ChatGPTCloudWeb.Endpoint
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: ChatGPTCloud.Supervisor)
  end

  @impl true
  def config_change(changed, _new, removed) do
    ChatGPTCloudWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
