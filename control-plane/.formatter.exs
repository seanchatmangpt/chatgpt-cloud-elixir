[
  import_deps: [:ecto, :ecto_sql, :phoenix],
  plugins: [Phoenix.LiveView.HTMLFormatter],
  subdirectories: ["priv/*/migrations"],
  inputs: ["mix.exs", "*.{ex,exs}", "{config,lib,test}/**/*.{ex,exs}"]
]
