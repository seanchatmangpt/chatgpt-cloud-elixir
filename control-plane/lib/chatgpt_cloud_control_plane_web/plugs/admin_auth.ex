defmodule ChatGPTCloudWeb.AdminAuth do
  @moduledoc false

  def init(opts), do: opts

  def call(conn, _opts) do
    if Application.get_env(:chatgpt_cloud_control_plane, :browser_auth_required, true) do
      username = Application.fetch_env!(:chatgpt_cloud_control_plane, :admin_username)
      password = Application.fetch_env!(:chatgpt_cloud_control_plane, :admin_password)

      Plug.BasicAuth.basic_auth(conn,
        username: username,
        password: password,
        realm: "Process Intelligence"
      )
    else
      conn
    end
  end
end
