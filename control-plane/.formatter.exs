[
  import_deps: [
    :ash,
    :ash_archival,
    :ash_cloak,
    :ash_graphql,
    :ash_json_api,
    :ash_oban,
    :ash_postgres,
    :ash_state_machine,
    :ecto,
    :ecto_sql,
    :phoenix
  ],
  plugins: [Phoenix.LiveView.HTMLFormatter],
  subdirectories: ["priv/*/migrations"],
  inputs: ["mix.exs", "*.{ex,exs}", "{config,lib,test}/**/*.{ex,exs}"]
]
