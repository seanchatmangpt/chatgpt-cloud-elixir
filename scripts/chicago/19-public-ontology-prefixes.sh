#!/usr/bin/env bash
set -euo pipefail
# prove public semantic prefixes survive the real manifest parser.
python3 - "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import sys,tomllib
p=tomllib.load(open(sys.argv[1],"rb"))["ontology"]["prefixes"]
assert p["prov"]=="http://www.w3.org/ns/prov#"
assert p["dcterms"]=="http://purl.org/dc/terms/"
assert p["skos"]=="http://www.w3.org/2004/02/skos/core#"
assert p["odrl"]=="http://www.w3.org/ns/odrl/2/"
PY
printf 'CHICAGO_PROBE ALIVE edge=19-public-ontology-prefixes\n'
