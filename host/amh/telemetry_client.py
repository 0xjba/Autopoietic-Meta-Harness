import asyncio
from typing import Awaitable, Callable

from bleak import BleakClient, BleakScanner

from amh.telemetry import TELEMETRY_CHAR_UUID, Sample, parse_sample

DEVICE_NAME = "AMH-Node"


async def find_device(name: str = DEVICE_NAME, timeout: float = 15.0):
    return await BleakScanner.find_device_by_name(name, timeout=timeout)


async def stream(on_sample: Callable[[Sample], Awaitable[None]], name: str = DEVICE_NAME):
    device = await find_device(name)
    if device is None:
        raise RuntimeError(f"device {name!r} not found")

    async with BleakClient(device) as client:
        async def handler(_char, data: bytearray):
            await on_sample(parse_sample(bytes(data)))

        await client.start_notify(TELEMETRY_CHAR_UUID, handler)
        while client.is_connected:
            await asyncio.sleep(1.0)
