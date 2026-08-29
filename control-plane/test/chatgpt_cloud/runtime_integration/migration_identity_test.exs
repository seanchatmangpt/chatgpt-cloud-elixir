defmodule ChatGPTCloud.RuntimeIntegration.MigrationIdentityTest do
  use ExUnit.Case, async: true

  alias ChatGPTCloud.RuntimeIntegration.MigrationIdentity

  test "migration identity includes source head and schema version" do
    sha = String.duplicate("b", 40)
    identity = MigrationIdentity.new(sha, 7)
    assert identity.subject_sha == sha
    assert identity.schema_version == 7
    assert byte_size(identity.digest) == 64
  end
end
