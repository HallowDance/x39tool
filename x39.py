"""Config library for the Temu "X-39 Pro" (Puya 36b7:fd13), a Redragon M908 protocol clone.

Protocol (feature reports on the 0xFFA0 interface, see NOTES.md):
  02 f5 00                      start session (required before every command batch)
  02 f2 <lo> <hi> <len>         read <len> (<=8) bytes; reply via GET_FEATURE 2, data at [7:]
  02 f3 <lo> <hi> <len> 0 0 0 d write <len> (<=8) bytes; a write ends read access until next f5
  02 f5 01                      finish session (commits writes)
"""
import os, time, hidio

SETF = lambda n: hidio._ioc(3, 0x06, n)

MEM_SIZE = 0x480                       # config area we manage (0x000-0x47f)
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')

ACTIVE_PROFILE = 0x2c
PROFILE_BASES = [0x40, 0x100, 0x1b0, 0x260, 0x310]
POLLING = [0x32, 0x34, 0x36, 0x38, 0x3a]          # per profile
LIGHTING = [0x448 + 8 * p for p in range(5)]      # 80 R G B mode speed mode2 brightness

# offsets inside a profile block
P_STAGE_COUNT, P_CURRENT_STAGE, P_DPI, P_BUTTONS = 0x00, 0x02, 0x04, 0x42
DPI_STAGE_SIZE, BUTTON_SIZE = 6, 4

BUTTON_SLOTS = [  # (slot, label); slots 19-21 are unused on this mouse
    (0, 'Left click'), (1, 'Right click'), (2, 'Middle click'), (3, 'Fire button'),
    (4, 'DPI + button'), (5, 'DPI − button'),
    *[(6 + i, f'Side button {i + 1}') for i in range(12)],
    (18, 'Top button (profile)'), (22, 'Scroll up'), (23, 'Scroll down'),
]

MOUSE_ACTIONS = {  # 4-byte button codes (from mouse_m908, matching this mouse's defaults)
    'Left click': (0x81, 0, 0, 0), 'Right click': (0x82, 0, 0, 0), 'Middle click': (0x83, 0, 0, 0),
    'Back': (0x84, 0, 0, 0), 'Forward': (0x85, 0, 0, 0),
    'DPI cycle': (0x88, 0, 0, 0), 'DPI −': (0x89, 0, 0, 0), 'DPI +': (0x8a, 0, 0, 0),
    'Scroll up': (0x8b, 0, 0, 0), 'Scroll down': (0x8c, 0, 0, 0),
    'Profile switch': (0x8d, 0, 0, 0), 'Profile +': (0x94, 0, 0, 0), 'Profile −': (0x95, 0, 0, 0),
    'Fire (3× left click)': (0x99, 0x81, 0x03, 0x0a),
    'LED mode switch': (0x9b, 0x04, 0, 0), 'DPI LED toggle': (0x9b, 0x01, 0, 0),
    'Play/Pause': (0x8e, 0x01, 0xcd, 0), 'Next track': (0x8e, 0x01, 0xb5, 0),
    'Previous track': (0x8e, 0x01, 0xb6, 0), 'Volume up': (0x8e, 0x01, 0xe9, 0),
    'Volume down': (0x8e, 0x01, 0xea, 0), 'Mute': (0x8e, 0x01, 0xe2, 0),
    'Disabled': (0, 0, 0, 0),
}
KEY_CODE = 0x90  # 90 <modifier mask> <HID usage> 00
MODIFIERS = {'Ctrl': 0x01, 'Shift': 0x02, 'Alt': 0x04, 'Super': 0x08}

def _hid_keys():
    keys = {chr(ord('a') + i): 0x04 + i for i in range(26)}
    keys.update({str(d): 0x1e + (d - 1) for d in range(1, 10)}); keys['0'] = 0x27
    keys.update({f'F{i}': 0x3a + i - 1 for i in range(1, 13)})
    keys.update({'Enter': 0x28, 'Esc': 0x29, 'Backspace': 0x2a, 'Tab': 0x2b, 'Space': 0x2c,
                 '-': 0x2d, '=': 0x2e, '[': 0x2f, ']': 0x30, '\\': 0x31, ';': 0x33, "'": 0x34,
                 '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38, 'CapsLock': 0x39, 'PrtSc': 0x46,
                 'ScrLk': 0x47, 'Pause': 0x48, 'Insert': 0x49, 'Home': 0x4a, 'PgUp': 0x4b,
                 'Delete': 0x4c, 'End': 0x4d, 'PgDn': 0x4e, 'Right': 0x4f, 'Left': 0x50,
                 'Down': 0x51, 'Up': 0x52, 'KP/': 0x54, 'KP*': 0x55, 'KP-': 0x56, 'KP+': 0x57,
                 'KPEnter': 0x58, **{f'KP{d}': 0x59 + d - 1 for d in range(1, 10)}, 'KP0': 0x62,
                 'KP.': 0x63})
    return keys
HID_KEYS = _hid_keys()
HID_NAMES = {v: k for k, v in HID_KEYS.items()}

LIGHT_MODES = {  # this firmware's own 5 effects (mode, mode2), learned from its LED-mode-switch cycle
    'Off': (0x00, 0x03), 'Solid colour': (0x01, 0x01), 'Breathing': (0x02, 0x01),
    'Rainbow': (0x03, 0x01), 'Blinking': (0x04, 0x01),
}
POLLING_RATES = {125: 8, 250: 4, 500: 2, 1000: 1}


def describe_button(code):
    code = tuple(code)
    if code[0] == KEY_CODE:
        mods = [n for n, bit in MODIFIERS.items() if code[1] & bit]
        return '+'.join(mods + [HID_NAMES.get(code[2], f'key 0x{code[2]:02x}')])
    for name, c in MOUSE_ACTIONS.items():
        if c[0] == code[0] and (c[0] not in (0x8e, 0x9b) or c[1:3] == code[1:3]):
            return name
    return 'Unknown (' + ' '.join(f'{b:02x}' for b in code) + ')'

def key_code(key, mods=()):
    mask = 0
    for m in mods:
        mask |= MODIFIERS[m]
    return (KEY_CODE, mask, HID_KEYS[key], 0)


class Mouse:
    def __init__(self):
        self.fd = os.open(hidio.find_vendor_hidraw(), os.O_RDWR)

    def close(self):
        os.close(self.fd)

    def _send(self, payload):
        buf = bytearray([2]) + bytearray(payload).ljust(15, b'\0')
        import fcntl
        fcntl.ioctl(self.fd, SETF(len(buf)), buf, True)

    def _start(self):
        self._send(b'\xf5\x00')

    def _read8(self, addr, n=8):
        for attempt in range(3):
            self._send(bytes([0xf2, addr & 0xff, addr >> 8, n]))
            r = hidio.get_feature(self.fd, 2, 15)
            if r[1] | (r[2] << 8) == addr and r[3] == n:
                return r[7:7 + n]
            self._start()  # session was interrupted (e.g. another program talked to the mouse)
        raise IOError(f'bad read reply at {addr:#x}: {r.hex(" ")}')

    def read_memory(self, start=0, end=MEM_SIZE):
        self._start()
        return bytes(b''.join(self._read8(a, min(8, end - a)) for a in range(start, end, 8)))

    def write_changes(self, old, new):
        """Write only bytes that differ, in <=8-byte runs, then verify by reading back."""
        runs, i = [], 0
        while i < len(new):
            if old[i] != new[i]:
                j = i
                while j < len(new) and j - i < 8 and old[j] != new[j]:
                    j += 1
                runs.append((i, new[i:j])); i = j
            else:
                i += 1
        if not runs:
            return 0
        self._start()
        for addr, data in runs:
            self._send(bytes([0xf3, addr & 0xff, addr >> 8, len(data), 0, 0, 0]) + bytes(data))
        self._send(b'\xf5\x01')
        time.sleep(0.05)
        check = self.read_memory(0, len(new))
        bad = [a for a, d in runs if check[a:a + len(d)] != bytes(d)]
        if bad:
            raise IOError('verify failed at ' + ', '.join(hex(a) for a in bad))
        return len(runs)

    def apply_profile_switch(self):
        """Sequence the official software sends after changing the active profile."""
        self._start()
        for mask in (0x01, 0x08, 0x04, 0x02, 0x08):
            self._send(bytes([0xf1, 0x02, mask]))
        self._send(b'\xf5\x01')


def backup(mem, tag='auto'):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = os.path.join(BACKUP_DIR, f'{time.strftime("%Y%m%d-%H%M%S")}-{tag}.bin')
    open(path, 'wb').write(mem)
    return path


class Config:
    """Editable view over a memory image."""
    def __init__(self, mem):
        self.mem = bytearray(mem)

    def u16(self, a): return self.mem[a] | (self.mem[a + 1] << 8)
    def set_u16(self, a, v): self.mem[a], self.mem[a + 1] = v & 0xff, v >> 8

    @property
    def active_profile(self): return self.mem[ACTIVE_PROFILE]
    @active_profile.setter
    def active_profile(self, p): self.mem[ACTIVE_PROFILE] = p

    def dpi_stages(self, p):
        b = PROFILE_BASES[p] + P_DPI
        return [(bool(self.mem[b + 6 * i]), self.u16(b + 6 * i + 1), self.u16(b + 6 * i + 3)) for i in range(5)]

    def set_dpi_stage(self, p, i, enabled, value):
        a = PROFILE_BASES[p] + P_DPI + 6 * i
        self.mem[a] = 1 if enabled else 0
        self.set_u16(a + 1, value); self.set_u16(a + 3, value)

    def current_stage(self, p): return self.mem[PROFILE_BASES[p] + P_CURRENT_STAGE]
    def set_current_stage(self, p, s): self.mem[PROFILE_BASES[p] + P_CURRENT_STAGE] = s

    def button(self, p, slot):
        a = PROFILE_BASES[p] + P_BUTTONS + BUTTON_SIZE * slot
        return tuple(self.mem[a:a + 4])

    def set_button(self, p, slot, code):
        a = PROFILE_BASES[p] + P_BUTTONS + BUTTON_SIZE * slot
        self.mem[a:a + 4] = bytes(code)

    def lighting(self, p):
        a = LIGHTING[p]
        _, r, g, b, mode, speed, mode2, bright = self.mem[a:a + 8]
        name = next((n for n, (m1, m2) in LIGHT_MODES.items() if m1 == mode),
                    f'Unknown ({mode:02x} {mode2:02x})')
        return {'mode': name, 'color': (r, g, b), 'speed': speed, 'brightness': bright}

    def set_lighting(self, p, mode=None, color=None, speed=None, brightness=None):
        a = LIGHTING[p]
        if mode is not None:
            m1, m2 = LIGHT_MODES[mode]
            self.mem[a + 4] = m1
            self.mem[a + 6] = m2
        if color is not None: self.mem[a + 1:a + 4] = bytes(color)
        if speed is not None: self.mem[a + 5] = speed
        if brightness is not None: self.mem[a + 7] = brightness

    def polling(self, p):
        return next((hz for hz, c in POLLING_RATES.items() if c == self.mem[POLLING[p]]), None)

    def set_polling(self, p, hz): self.mem[POLLING[p]] = POLLING_RATES[hz]
