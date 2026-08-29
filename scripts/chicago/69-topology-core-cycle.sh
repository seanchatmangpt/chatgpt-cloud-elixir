#!/usr/bin/env bash
set -euo pipefail
p="$CONSUMER_A/manufacturing/generated/autonomic-manufacturing.mmd"; for e in 'O[Admitted semantic objective O*] --> D' 'D --> G' 'G --> C' 'C --> S' 'S --> R' 'R --> K' 'K --> M' 'M --> G'; do grep -Fq "$e" "$p"; done
