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
    live "/human-value", HumanValueLive, :index
  end

  scope "/api", ChatGPTCloudWeb do
    pipe_through :api
    post "/v1/ocel/batches", IngestController, :create

    get "/v1/swarm/work", WorkController, :index
    post "/v1/swarm/work", WorkController, :create
    post "/v1/swarm/work/:work_item_id/claim", WorkController, :claim
    post "/v1/swarm/work/:work_item_id/progress", WorkController, :progress
    post "/v1/swarm/work/:work_item_id/complete", WorkController, :complete
    post "/v1/swarm/work/:work_item_id/block", WorkController, :block
    post "/v1/swarm/work/:work_item_id/refuse", WorkController, :refuse
    post "/v1/swarm/project2/import", WorkController, :import_project2
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
