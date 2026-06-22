#!/usr/bin/env bash
set -euo pipefail

# Provisions the full environment and verifies it. See PREREQUISITES.md for the
# reference platform and pinned versions.

cd "$(dirname "$0")/.."

./scripts/setup_embedded.sh
./scripts/setup_model.sh
./scripts/setup_host.sh

(cd host && .venv/bin/python -m pytest -q)

LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
  arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense firmware/amh_node >/dev/null
echo "firmware compiles"

echo "bootstrap complete"
