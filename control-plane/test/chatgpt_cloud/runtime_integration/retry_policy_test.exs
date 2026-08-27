defmodule ChatGPTCloud.RuntimeIntegration.RetryPolicyTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloud.RuntimeIntegration.RetryPolicy

  test "retry budgets terminate deterministically" do
    assert RetryPolicy.retry?(:qualification, 2)
    refute RetryPolicy.retry?(:qualification, 3)
    refute RetryPolicy.retry?(:unknown, 0)
  end
end
