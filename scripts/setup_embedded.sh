#!/usr/bin/env bash
set -euo pipefail

INDEX="https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json"

arduino-cli config init --overwrite
arduino-cli config add board_manager.additional_urls "$INDEX"
arduino-cli core update-index
arduino-cli core install Seeeduino:nrf52
arduino-cli lib install "Seeed Arduino LSM6DS3"
arduino-cli board listall | grep -i xiao
