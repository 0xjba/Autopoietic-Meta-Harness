import asyncio
from typing import Awaitable, Callable

from bleak import BleakClient, BleakScanner


class BleTelemetrySource:
    def __init__(self, device_name: str, char_uuid: str):
        self.device_name = device_name
        self.char_uuid = char_uuid

    async def stream(self, on_frame: Callable[[bytes], Awaitable[None]]) -> None:
        device = await BleakScanner.find_device_by_name(self.device_name, timeout=15.0)
        if device is None:
            raise RuntimeError(f"device {self.device_name!r} not found")

        async with BleakClient(device) as client:
            async def handler(_char, data: bytearray):
                await on_frame(bytes(data))

            await client.start_notify(self.char_uuid, handler)
            while client.is_connected:
                await asyncio.sleep(1.0)
