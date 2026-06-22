import argparse
import asyncio

import ollama

from amh.adapters.nrf52.arduino_deployer import Nrf52ArduinoDeployer
from amh.adapters.nrf52.ble_source import BleTelemetrySource
from amh.core.controller import Controller
from amh.core.settings import load_settings
from amh.usecases.ahrs.objective import AhrsUseCase


def main():
    parser = argparse.ArgumentParser(prog="amh")
    parser.add_argument("--config", default="amh/config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings(args.config)
    if args.dry_run:
        settings.dry_run = True

    usecase = AhrsUseCase(battery_threshold=settings.battery_threshold)
    source = BleTelemetrySource(usecase.device_name, usecase.char_uuid)
    deployer = Nrf52ArduinoDeployer(settings.fqbn, settings.sketch_dir,
                                    settings.config_h_path, settings.port)
    controller = Controller(settings, source, deployer, usecase, ollama.Client())
    asyncio.run(controller.run())


if __name__ == "__main__":
    main()
