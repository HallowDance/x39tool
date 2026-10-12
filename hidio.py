"""Minimal hidraw access for the Puya-based 'ARM USB Gaming Mouse' (36b7:fd13). Read-only helpers."""
import os, fcntl, glob

VID, PID = 0x36B7, 0xFD13

def _ioc(direction, nr, size):
    return (direction << 30) | (size << 16) | (ord('H') << 8) | nr

def find_vendor_hidraw():
    """hidraw node of the vendor config interface (usage page 0xFFA0)."""
    for h in sorted(glob.glob('/sys/class/hidraw/*')):
        uevent = open(h + '/device/uevent').read().upper()
        if f'{VID:08X}:{PID:08X}' not in uevent:
            continue
        if b'\x06\xa0\xff' in open(h + '/device/report_descriptor', 'rb').read():
            return '/dev/' + os.path.basename(h)
    raise SystemExit('mouse vendor interface not found')

def get_feature(fd, report_id, size):
    """HIDIOCGFEATURE: returns `size` data bytes (report id stripped)."""
    buf = bytearray(size + 1)
    buf[0] = report_id
    n = fcntl.ioctl(fd, _ioc(3, 0x07, len(buf)), buf, True)
    return bytes(buf[1:n])

FEATURE_SIZES = {2: 15, 3: 63, 4: 255, 5: 1023, 6: 2047}
