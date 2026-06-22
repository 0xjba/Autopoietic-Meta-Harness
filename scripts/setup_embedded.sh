#!/usr/bin/env bash
set -euo pipefail

INDEX="https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json"

# The Seeed nRF52 core's UF2/DFU build steps invoke a bare `python`, which macOS
# does not provide. Expose one if absent.
if ! command -v python >/dev/null 2>&1; then
  ln -sf "$(command -v python3)" "$(dirname "$(command -v python3)")/python"
fi

arduino-cli config init --overwrite
arduino-cli config add board_manager.additional_urls "$INDEX"
arduino-cli core update-index
arduino-cli core install Seeeduino:nrf52@1.1.13
arduino-cli lib install "Seeed Arduino LSM6DS3@2.0.5"
arduino-cli board listall | grep -i xiao
