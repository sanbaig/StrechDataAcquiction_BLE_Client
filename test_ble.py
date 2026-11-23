
import asyncio
from bleak import BleakScanner, BleakClient

DATA_CHAR_UUID = "12345679-1234-5678-1234-56789abcdef0"

packet_count = 0

def notification_handler(sender, data):
    global packet_count

    packet_count += 1

    if len(data) != 4:
        print("Invalid packet:", data.hex())
        return

    ch1 = int.from_bytes(data[0:2], byteorder="little")
    ch2 = int.from_bytes(data[2:4], byteorder="little")

    print(f"Packet {packet_count}: CH1={ch1}, CH2={ch2}")

async def main():
    print("Scanning for StretchSense...")

    devices = await BleakScanner.discover(timeout=10)

    target = next(
        (d for d in devices if d.name and "StretchSense" in d.name),
        None
    )

    if target is None:
        print("StretchSense not found.")
        return

    print("Found:", target.name, target.address)

    async with BleakClient(target.address) as client:
        print("Connected:", client.is_connected)

        await client.start_notify(
            DATA_CHAR_UUID,
            notification_handler
        )

        print("Receiving data for 10 seconds...")

        await asyncio.sleep(10)

        await client.stop_notify(DATA_CHAR_UUID)

        print("Total packets received:", packet_count)

asyncio.run(main())
