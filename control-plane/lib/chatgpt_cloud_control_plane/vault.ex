defmodule ChatGPTCloud.Vault do
  @moduledoc "Runtime-selected Cloak vault for encrypted control-plane attributes."
  use Cloak.Vault, otp_app: :chatgpt_cloud_control_plane
end
