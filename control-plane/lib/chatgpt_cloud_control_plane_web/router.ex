defmodule ChatGPTCloudWeb.Router do
  use ChatGPTCloudWeb, :router
  import AshAdmin.Router

  pipeline :browser do
    plug :accepts, ["html"]
    plug :fetch_session
    plug :fetch_live_flash
    plug :put_root_layout, html: {ChatGPTCloudWeb.Layouts, :root}
    plug :protect_from_forgery
    plug :put_secure_browser_headers
    plug ChatGPTCloudWeb.AdminAuth
  end

  pipeline :api do
    plug :accepts, ["json"]
    plug ChatGPTCloudWeb.OcelAuth
  end

  pipeline :public do
    plug :accepts, ["json"]
  end

  scope "/", ChatGPTCloudWeb do
    pipe_through :browser

    live "/", OcelLive, :index
    live "/process-intelligence/live", OcelLive, :index
  end

  scope "/api", ChatGPTCloudWeb do
    pipe_through :api
    post "/v1/ocel/batches", IngestController, :create
  end

  scope "/api" do
    pipe_through :api
    forward "/json", ChatGPTCloudWeb.JsonApiRouter
  end

  scope "/graphql" do
    pipe_through :api
    forward "/", Absinthe.Plug, schema: ChatGPTCloudWeb.GraphqlSchema
  end

  scope "/mcp" do
    pipe_through :api

    forward "/", AshAi.Mcp.Router,
      tools: [
        :list_qualifications,
        :list_cost_observations,
        :read_dfcm_memory,
        :upsert_dfcm_memory,
        :snapshot_dfcm_project,
        :list_project_items
      ],
      otp_app: :chatgpt_cloud_control_plane
  end

  scope "/", ChatGPTCloudWeb do
    pipe_through :public
    get "/healthz", HealthController, :show
  end

  scope "/" do
    pipe_through :browser
    ash_admin("/admin")
  end
end
