#!/usr/bin/env bash
set -euo pipefail
# prove generation consumed the declared real ontology source.
source="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["ontology"]["source"])' "$CONSUMER_A/manufacturing/ggen.toml")"
test "$source" = ontology.ttl
test -s "$CONSUMER_A/manufacturing/$source"
grep -q 'https://chatman.ai/chatgpt-cloud/capability#' "$CONSUMER_A/manufacturing/$source"
printf 'CHICAGO_PROBE ALIVE edge=18-ontology-source\n'
