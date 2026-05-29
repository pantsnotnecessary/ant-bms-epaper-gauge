# ANT-BMS e-Paper SOC + Temp Gauge

A fully standalone battery gauge for an electric motorcycle (or any pack with an
**ANT BMS**). A **Waveshare ESP32-S3 1.54" e-Paper** module reads the BMS over BLE
and shows **state of charge, pack temperature, voltage, current, and Ah remaining**
on a 200×200 e-paper screen. No phone, no network, no Home Assistant — it runs off
bike power and the e-paper keeps the last reading visible even when powered off.

Built with [ESPHome](https://esphome.io) + the
[`syssi/esphome-ant-bms`](https://github.com/syssi/esphome-ant-bms) external component.

> **Why it exists:** the rider overheated a pack and got stranded waiting for it to
> cool. This gauge puts SOC *and* a worst-case pack-temperature warning in your
> line of sight, so you can ease off before the BMS hits its 60 °C cutoff.

## Features

- **Zero-config pairing.** Auto-discovers the BMS by BLE name (`ANT-BLE…`) and locks
  onto the nearest one by signal strength. **No MAC address to look up or edit** —
  flash it and it finds your pack. Swap battery packs and it just re-finds the new one.
- **Glanceable overheat warning.** Shows the hottest of the 4 pack temperature
  sensors; at ≥ 50 °C the reading flips to `HOT` and a thick border frames the whole
  screen.
- **Truly standalone & low power.** The e-paper holds its image with zero power, so
  the panel is powered only for the ~1.5 s it takes to refresh.

## Hardware

| Part | Notes |
|------|-------|
| **Waveshare ESP32-S3-ePaper-1.54 (V2)** | All-in-one ESP32-S3-PICO-1 + 200×200 B/W e-paper (SSD1681). The **V2** revision — pin map below is V2-specific. |
| **ANT BMS (BLE, 2021+ protocol)** | Advertises as `ANT-BLE<model>-<suffix>`. Uses the `ant_bms_ble` platform (not `ant_bms_old_ble`). No password needed for reading. |

## Quick start

```bash
pip install esphome
esphome run bms-gauge.yaml          # first flash over USB-C; pick the COM/tty port
```

That's it. On boot the screen stays dark until it finds and connects to the BMS,
then it shows live data and refreshes every 30 s. If your BMS is asleep, wake it once
with the ANT phone app and close the app — the gauge grabs the connection.

### Tunables (top of `bms-gauge.yaml`)

| Substitution | Default | Meaning |
|---|---|---|
| `bms_name_prefix` | `ANT-BLE` | BLE name prefix that identifies your BMS. |
| `hot_temp_c` | `50` | On-screen overheat warning threshold (°C). |
| `bms_mac` | (a real MAC) | Seed/fallback only — auto-discovery overrides it at runtime. Safe to leave as-is. |

## What we had to reverse-engineer

This board + BMS combination has several traps that aren't documented anywhere
obvious. If you're fighting a similar setup, this is the useful part:

1. **`EPD_PWR` (GPIO6) is ACTIVE-LOW.** Driving it *high* turns the panel **off**.
   Per Waveshare's own V2 board-support source: `gpio 0 = ON, 1 = OFF`. The pin is
   set `inverted: true` so ESPHome's `turn_on` drives it low. Get this wrong and the
   panel never powers up, `BUSY` never releases, and every refresh logs
   `Timeout while displaying image!`.

2. **The real V2 GPIO map** (from Waveshare's `epaper_config.h`, *not* the generic
   1.54" wiki pinout, which is wrong for this board):

   | Signal | GPIO |
   |---|---|
   | DC | 10 |
   | CS | 11 |
   | SCK / CLK | 12 |
   | MOSI | 13 |
   | RST | 9 |
   | BUSY | 8 |
   | PWR_EN | 6 (active-low) |

   Panel model string: `1.54inv2` (SSD1681).

3. **Powering the e-paper desensitizes the onboard BLE antenna.** They share one tiny
   PCB. If you keep the panel powered, the ESP32 can't reliably *acquire* the BMS
   connection (it would sit on `Connecting → Not connected` indefinitely). The fix:
   keep the panel **off** until BLE connects, then power it **only during each
   refresh**. This also happens to be the correct low-power design.

4. **Bump the main task stack via `sdkconfig_options`, not a build flag.** The ANT
   component can stack-overflow on boot. Set
   `CONFIG_ESP_MAIN_TASK_STACK_SIZE: "8192"` under `esp32.framework.sdkconfig_options`.
   Do **not** use `-DCONFIG_ESP_MAIN_TASK_STACK_SIZE=...` as a build flag — it
   redefines the symbol already in `sdkconfig.h` and fails the build under `-Werror`.

5. **Auto-discovery instead of a hardcoded MAC.** `esp32_ble_tracker`'s
   `on_ble_advertise` watches for the `ANT-BLE` name prefix, tracks the strongest
   RSSI, and calls `ble_client.set_address()` at runtime. The configured `mac_address`
   is just a seed/fallback.

## Display layout (200×200)

```
┌──────────────────┐
│       55%        │  SOC (large)
│      32C         │  hottest pack sensor  → "HOT 52C" + border at ≥ threshold
│      78.0V       │  pack voltage
│   3A   44.2Ah    │  current + Ah remaining
│ ████████░░░░░░░░ │  SOC bar
└──────────────────┘
```

## Known quirks

- A single `Timeout while displaying image!` at boot is normal — that's the display's
  setup refresh firing before the panel is powered. Harmless.
- `Dropped N BLE events` / an occasional `Invalid frame length` line up with the
  ~1.5 s blocking e-paper refresh: notifications queue up while the CPU is busy and one
  status frame gets mangled. The next poll is clean and the displayed data still
  updates. Cosmetic for a slow gauge.

## Files

- **`bms-gauge.yaml`** — the gauge firmware.
- **`scanner.yaml`** — optional standalone BLE scanner (auto-discovery makes it
  unnecessary, kept for debugging).
- **`tools/ble-scan.ps1`** — Windows BLE scanner (lists nearby devices + MACs).
- **`tools/ble-probe.py`** — connects to a BMS and dumps its GATT services (handy
  when the ESP32's own radio is too weak to debug with).

## Credits

- [`syssi/esphome-ant-bms`](https://github.com/syssi/esphome-ant-bms) — the ANT BMS
  BLE component doing the real protocol work.
- [Waveshare ESP32-S3-ePaper-1.54](https://github.com/waveshareteam/ESP32-S3-ePaper-1.54)
  — board source that revealed the active-low power pin and V2 pin map.

## License

MIT — see [LICENSE](LICENSE).
