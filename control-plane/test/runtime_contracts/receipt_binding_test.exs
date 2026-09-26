defmodule ChatGPTCloudControlPlane.RuntimeContracts.ReceiptBindingTest do
  use ExUnit.Case, async: true
  alias ChatGPTCloudControlPlane.RuntimeContracts.ReceiptBinding
  test "binds subject authority consequence replay and standing" do
    receipt = %{subject: "s", authority: "a", consequence: "c", replay: "r", standing: :alive}
    assert :ok = ReceiptBinding.validate(receipt)
    assert {:error, {:receipt_field_missing, :replay}} = ReceiptBinding.validate(Map.delete(receipt, :replay))
  end
end
