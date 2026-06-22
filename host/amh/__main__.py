import argparse
import asyncio

from amh.loop import run
from amh.settings import load_settings


def main():
    parser = argparse.ArgumentParser(prog="amh")
    parser.add_argument("--config", default="amh/config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings = load_settings(args.config)
    if args.dry_run:
        settings.dry_run = True
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
