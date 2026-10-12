# Protocol notes: Puya-based "ARM USB Gaming Mouse" (36b7:fd13)

Everything here was confirmed on the device unless marked otherwise.

## Identification

| | |
|---|---|
| USB ID | `36b7:fd13` (vendor 0x36B7 = Puya Semiconductor, the default VID in Puya's SDK examples) |
| Product string | `ARM USB Gaming Mouse`, manufacturer `ARM`, bcdDevice 1.26 |
| MCU | Puya PY32 series (most likely PY32F071/F072, the USB-capable parts) |
| Sold as | E-YOOSO X-39 Pro (Temu listing). Genuine E-YOOSO X-39 software targets Holtek `04d9:*` and does not work. |
| Interfaces | 0 mouse (67-byte report descriptor), 1 keyboard (47), 2 vendor/consumer (106) |

The descriptor sizes, memory layout and button codes match the **Redragon M908 Impact** (Holtek `04d9:fc4d`).
This firmware is a clone of that protocol, documented by [dokutan/mouse_m908](https://github.com/dokutan/mouse_m908).

## Transport

Interface 2, usage page `0xFFA0`. Feature reports 2 (15 B), 3 (63 B), 4 (255 B), 5 (1023 B), 6 (2047 B).
Input reports 7 and 8 (7 B). All commands are `SET_FEATURE` on report 2; replies come back via `GET_FEATURE` report 2.

| Command | Bytes (after report id 02) | Notes |
|---|---|---|
| Start session | `f5 00` | Required before every batch of commands |
| Read | `f2 <addr lo> <addr hi> <len>` | Reply: `08 <addr lo> <addr hi> <len> 00 fa fa <data…>`. Use len ≤ 8; 32-byte reads via report 3 sometimes returned stale data. |
| Write | `f3 <addr lo> <addr hi> <len> 00 00 00 <data…>` | len ≤ 8. Several writes may share one session. After a write, reads are ignored until the next `f5 00`. |
| Finish | `f5 01` | Commits the writes. Without it, writes are discarded. |
| Apply | `f1 02 <mask>` | Sent by the official M908 software after profile changes. Not required for DPI/lighting/buttons here. |

`SET_FEATURE` on report 5 is rejected (EPIPE). `GET_FEATURE` 5/6 returns the I/O buffer (the last reply, then a settings mirror).
Changes take effect immediately, with no replug needed.

## Memory map

| Address | Meaning |
|---|---|
| `0x20 + 2p` | Scroll speed per profile (M908 layout, unverified) |
| `0x2c` | Active profile, 0-based |
| `0x32 + 2p` | Polling rate per profile: `1`=1000 Hz, `2`=500, `4`=250, `8`=125 (M908 values; dropdown not yet verified) |
| profile base | `0x40`, `0x100`, `0x1b0`, `0x260`, `0x310` for profiles 1–5 |
| base + `0x00` | Number of DPI stages (5) |
| base + `0x02` | Current DPI stage, 0-based |
| base + `0x04 + 6i` | DPI stage *i*: `enabled, X lo, X hi, Y lo, Y hi, 00`. Defaults are levels 5/10/20/30/40; the DPI per level is not calibrated. |
| base + `0x42 + 4s` | Button slot *s* (24 slots, 4 bytes each) |
| `0x448 + 8p` | Lighting per profile: `80, R, G, B, mode, speed, mode2, brightness` |

### Button slots
0 left, 1 right, 2 middle, 3 fire, 4 DPI+, 5 DPI−, 6–17 side buttons 1–12, 18 top button, 19–21 unused, 22 scroll up, 23 scroll down.

### Button codes (4 bytes)
`81` left, `82` right, `83` middle, `84` back, `85` forward, `88` DPI cycle, `89` DPI−, `8a` DPI+, `8b`/`8c` scroll up/down,
`8d` profile switch, `94`/`95` profile ±, `99 81 03 0a` fire (3× left), `9b 04` LED mode switch, `9b 01` DPI LED toggle,
`8e 01 <usage>` media key, `90 <modifier mask> <HID usage> 00` keyboard key (mask: 1 Ctrl, 2 Shift, 4 Alt, 8 Super), `00` disabled.

### Lighting (this firmware's own values, NOT the M908 table)
- `mode` / `mode2`: `00/03` off, `01/01` solid colour, `02/01` breathing, `03/01` rainbow, `04/01` blinking
- `speed`: 1 = fastest … 8 = slowest (firmware default 5)
- `brightness`: 0 off, 1–3 dim → bright; values above 3 look the same as 3 (firmware default 3)

## Events (input report 8, unsolicited)
- `01 <profile>`: profile changed (bottom "mod switch" button)
- `02 <stage>`: DPI stage changed
- `09 00 <mode> <speed> <mode2> <brightness>`: lighting changed via the LED-mode-switch function
