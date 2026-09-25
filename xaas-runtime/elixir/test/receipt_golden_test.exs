defmodule ChatGPTCloud.Xaas.ReceiptGoldenTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.Xaas.Receipt

  @fixture Path.expand("fixtures/receipt_golden.json", __DIR__)
  @expected Path.expand("fixtures/receipt_golden.sha256", __DIR__)

  # The same two files are read by tests/test_xaas_runtime.py (Python canonical_json)
  # and are the parity target for xaas Xaas.Tunnel.Receipt.
  test "golden receipt digest equals the committed sha256 (Python canonical_json parity)" do
    value = @fixture |> File.read!() |> JSON.decode!()
    expected = @expected |> File.read!() |> String.trim()

    assert Receipt.digest(value) == expected
    assert expected == "7d98905d89388c098e14c63226356f8b4cab61d6422c1017ea77e78162ef2870"
  end

  test "canonical form: sorted keys, compact separators, raw UTF-8, Python escapes" do
    ls = <<0x2028::utf8>>

    assert Receipt.canonical(%{"b" => 1, "a" => [true, nil, "é/" <> ls]}) ==
             ~s({"a":[true,null,"é/) <> ls <> ~s("],"b":1})

    assert Receipt.canonical("\"\\\b\f\n\r\t\u0001\u001f\u007f") ==
             ~S("\"\\\b\f\n\r\t\u0001\u001f) <> "\u007f\""

    assert Receipt.canonical(%{"Z" => 1, "z" => 2, "é" => 3, "10" => 4, "2" => 5}) ==
             ~s({"10":4,"2":5,"Z":1,"z":2,"é":3})
  end

  test "floats, invalid UTF-8 and duplicate keys are refused" do
    assert_raise ArgumentError, fn -> Receipt.canonical(%{"x" => 1.0}) end
    assert_raise ArgumentError, fn -> Receipt.canonical(<<0xFF>>) end
    assert_raise ArgumentError, fn -> Receipt.canonical(%{:a => 1, "a" => 2}) end
  end

  test "a one-byte mutation of the golden changes the digest (anti-vacuity)" do
    value = @fixture |> File.read!() |> JSON.decode!()
    expected = @expected |> File.read!() |> String.trim()

    refute Receipt.digest(put_in(value, ["identity", "idempotency_key"], "golden-002")) ==
             expected
  end

  test "verify_replay accepts the sealed digest and refuses a tampered one" do
    sealed = %{"epoch_id" => "e", "outcome" => "alive"}
    assert Receipt.verify_replay(sealed, Receipt.digest(sealed)) == :ok

    assert Receipt.verify_replay(sealed, Receipt.digest(%{sealed | "outcome" => "x"})) ==
             {:refused, :replay_digest_mismatch}
  end

  test "endpoint redaction and digest match Python endpoint_identity/endpoint_digest" do
    url = "https://Example.COM:8443/internal-api/execution/mcp"
    assert Receipt.endpoint_identity(url) == "https://<redacted-host>/internal-api/execution/mcp"

    assert Receipt.endpoint_digest(url) ==
             :crypto.hash(:sha256, "https://example.com:8443/internal-api/execution/mcp")
             |> Base.encode16(case: :lower)

    assert Receipt.endpoint_digest("https://example.com/internal-api/execution/mcp") ==
             :crypto.hash(:sha256, "https://example.com/internal-api/execution/mcp")
             |> Base.encode16(case: :lower)
  end
end
