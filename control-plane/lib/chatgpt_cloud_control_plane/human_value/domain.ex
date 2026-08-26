defmodule ChatGPTCloud.HumanValue do
  @moduledoc "Ash domain for dynamically acquired, provenance-bound human-value scenarios."

  use Ash.Domain

  resources do
    resource ChatGPTCloud.HumanValue.World
  end
end
