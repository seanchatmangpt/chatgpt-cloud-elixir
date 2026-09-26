import Config

# Ash 3.33+ refuses to compile resources until a string-length counting mode is chosen.
# :codepoints is Ash's recommendation and matches how SQL data layers count length.
config :ash, default_string_length_count: :codepoints
