defmodule ChatGPTCloudWeb do
  @moduledoc false

  def static_paths, do: ~w(assets robots.txt)

  def router do
    quote do
      use Phoenix.Router, helpers: false
      import Plug.Conn
      import Phoenix.Controller
      import Phoenix.LiveView.Router
    end
  end

  def controller do
    quote do
      use Phoenix.Controller, formats: [:html, :json]
      import Plug.Conn
    end
  end

  def live_view do
    quote do
      use Phoenix.LiveView
      import Phoenix.HTML
    end
  end

  def html do
    quote do
      use Phoenix.Component
      import Phoenix.HTML
    end
  end

  defmacro __using__(which) when is_atom(which), do: apply(__MODULE__, which, [])
end
