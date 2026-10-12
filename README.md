# x39tool

> **Credit:** nearly all of the protocol knowledge behind this tool comes from
> **[dokutan/mouse_m908](https://github.com/dokutan/mouse_m908)** (GPL-3.0), which reverse-engineered
> Redragon's mouse protocol. This mouse's firmware is a clone of the **Redragon M908 Impact** protocol, so
> their command format, memory layout and button/key code tables apply here almost unchanged.
> This project only adapts that work to one specific model: it confirms everything on the hardware and fills
> in what differs on this firmware (lighting modes, brightness/speed ranges, read/write session behaviour).
> If your mouse is a real Redragon, use mouse_m908 instead.

A Linux configurator (GUI + Python library) for a cheap MMO gaming mouse that identifies as
**`36b7:fd13` "ARM USB Gaming Mouse"**: a **Puya PY32**-based mouse sold on Temu as the
**E-YOOSO X-39 Pro**.

> **Only for this mouse/chip combination.** The genuine E-YOOSO X-39 / X-39 Pro uses a Holtek controller
> (`04d9:*`), and E-YOOSO's own software only supports that one. This tool is for the Puya-based
> version that no official software recognises. Check with `lsusb | grep 36b7:fd13`.

Features: DPI stages (enable, level, current stage), polling rate, lighting (off / solid / breathing /
rainbow / blinking, colour, speed, brightness), button remapping (mouse functions, media keys, keyboard keys
with modifiers) and active profile, for all 5 on-board profiles. Settings are stored on the mouse.

## Setup

Python 3 with tkinter (`pacman -S tk`). No other dependencies.

Allow non-root access to the mouse's raw HID device:

```sh
sudo cp 71-x39.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

Then unplug and replug the mouse.

## Usage

```sh
python3 x39gui.py
```

Pick the profile to edit, change settings and click **Apply to mouse**. Only changed bytes are written, and
each write is verified by reading it back. Before the first change in a session, the full settings area is saved
to `backup/`. **Restore backup…** writes one back. Left click cannot be remapped, so you can't lock yourself out.

Close any other program that talks to the mouse while applying settings.

## Files

| | |
|---|---|
| `x39gui.py` | Tkinter GUI |
| `x39.py` | Library: session/read/write protocol, memory map, code tables |
| `hidio.py` | hidraw lookup and feature-report ioctls |
| `PROTOCOL.md` | Protocol and memory-map notes |
| `research/` | Scripts used while reverse-engineering (event listener, write probe, lighting watcher, brightness test) |
| `71-x39.rules` | udev rule for hidraw access |

## Not done / unverified

- The DPI per level is not calibrated. The GUI shows level × 100 as a rough estimate.
- The polling-rate dropdown and switching the active profile from the GUI have not been tested on the device.
- Macros are not supported.

## Development note

Generative AI tools were used during development: for researching the hardware, reverse-engineering the
protocol on the device, and writing the code and documentation. All protocol details were verified on real
hardware.

## License

GPL-3.0-or-later. The code tables are derived from mouse_m908 (GPL-3.0).
