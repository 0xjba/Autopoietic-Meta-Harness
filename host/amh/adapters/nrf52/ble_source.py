import asyncio
from typing import Awaitable, Callable

from bleak import BleakClient, BleakScanner


class BleTelemetrySource:
    def __init__(self, service_uuid: str, char_uuid: str):
        self.service_uuid = service_uuid
        self.char_uuid = char_uuid

    async def stream(self, on_frame: Callable[[bytes], Awaitable[None]]) -> None:
        # Match on the advertised service UUID rather than the device name: the
        # 128-bit service UUID consumes the advertisement budget and truncates the
        # name, so the name is unreliable for discovery.
        target = self.service_uuid.lower()

        def has_service(_device, adv) -> bool:
            return target in [u.lower() for u in adv.service_uuids]

        device = await BleakScanner.find_device_by_filter(has_service, timeout=15.0)
        if device is None:
            raise RuntimeError(f"no device advertising service {self.service_uuid}")

        async with BleakClient(device) as client:
            async def handler(_char, data: bytearray):
                await on_frame(bytes(data))

            await client.start_notify(self.char_uuid, handler)
            while client.is_connected:
                await asyncio.sleep(1.0)
