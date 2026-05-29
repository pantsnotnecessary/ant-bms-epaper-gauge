import asyncio
import sys
from bleak import BleakClient, BleakScanner

# Pass your BMS MAC as the first arg:  python ble-probe.py AA:BB:CC:DD:EE:FF
# (find it with tools/ble-scan.ps1). Defaults to a placeholder.
MAC = sys.argv[1] if len(sys.argv) > 1 else "00:00:00:00:00:00"

frames = []

def make_handler(uuid):
    def handler(_char, data: bytearray):
        frames.append((uuid, bytes(data)))
        print(f"  NOTIFY {uuid}: {data.hex('.')}")
    return handler

async def main():
    print(f"Scanning for {MAC} ...")
    dev = await BleakScanner.find_device_by_address(MAC, timeout=15.0)
    if not dev:
        print("Not found advertising. Wake it via the ANT app, then rerun.")
        return
    print(f"Found: {dev.name} [{dev.address}]  — connecting...")

    async with BleakClient(dev, timeout=20.0) as client:
        print(f"CONNECTED: {client.is_connected}")
        print("\nGATT services / characteristics:")
        notify_chars = []
        write_chars = []
        for svc in client.services:
            print(f"  service {svc.uuid}")
            for ch in svc.characteristics:
                props = ",".join(ch.properties)
                print(f"    char {ch.uuid}  [{props}]")
                if "notify" in ch.properties:
                    notify_chars.append(ch.uuid)
                if "write" in ch.properties or "write-without-response" in ch.properties:
                    write_chars.append(ch.uuid)

        print(f"\nSubscribing to {len(notify_chars)} notify char(s)...")
        for u in notify_chars:
            try:
                await client.start_notify(u, make_handler(u))
            except Exception as e:
                print(f"  (could not subscribe {u}: {e})")

        # ANT new-protocol status poll: request the device status frame.
        # 7E A1 <cmd> 00 00 <len> ... ; the component polls a fixed request.
        # Try the known ANT-BLE status request command on each writable char.
        poll = bytes.fromhex("7EA1130000000000BEEB7EAA55")  # device-info style probe
        print("\nListening 12s for auto-pushed frames...")
        await asyncio.sleep(12)

        if not frames and write_chars:
            print("No auto-push; trying a poll write on writable chars...")
            for u in write_chars:
                try:
                    await client.write_gatt_char(u, poll, response=False)
                    print(f"  wrote poll to {u}")
                except Exception as e:
                    print(f"  (write failed {u}: {e})")
            await asyncio.sleep(8)

        print(f"\nTotal frames captured: {len(frames)}")

asyncio.run(main())
