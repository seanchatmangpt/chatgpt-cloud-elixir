defmodule ChatGPTCloud.Repo do
  use AshPostgres.Repo, otp_app: :chatgpt_cloud_control_plane
end
