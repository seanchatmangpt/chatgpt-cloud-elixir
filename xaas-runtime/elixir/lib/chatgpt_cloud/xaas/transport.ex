defmodule ChatGPTCloud.Xaas.Transport do
  @moduledoc """
  One request to the XaaS fabric scope. `path` is absolute from the XaaS base
  (e.g. `/internal-api/fabric/probe`); `opts` carries `:target` and `:timeout` (ms).

  Errors are typed so `ChatGPTCloud.Xaas.Fabric.classify/2` can mirror Python
  `classify_http`: `:network`, `:config`, `:redirect`, `:protocol`.
  """

  @type error_kind :: :network | :config | :redirect | :protocol
  @type result :: {:ok, pos_integer(), map() | list() | nil} | {:error, {error_kind, term()}}

  @callback request(
              method :: :get | :post,
              path :: String.t(),
              body :: map() | nil,
              opts :: keyword()
            ) :: result()
end
