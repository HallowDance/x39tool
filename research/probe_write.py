"""One controlled SET_FEATURE, with before/after snapshots and reply capture."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import os, sys, fcntl, select, time, hidio
SETF = lambda n: hidio._ioc(3, 0x06, n)

def snapshot(fd):
    return {rid: hidio.get_feature(fd, rid, size) for rid, size in hidio.FEATURE_SIZES.items()}

def drain(fd, secs):
    out, end = [], time.time() + secs
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r: out.append(os.read(fd, 4096))
    return out

def run(report_id, payload):
    dev = hidio.find_vendor_hidraw()
    fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)
    drain(fd, 0.2)
    before = snapshot(fd)
    buf = bytearray([report_id]) + bytearray(payload).ljust(hidio.FEATURE_SIZES[report_id], b'\0')
    print('SEND report', report_id, bytes(buf[1:17]).hex(' '), '...' if len(buf) > 17 else '')
    try:
        print('  result: accepted, ret', fcntl.ioctl(fd, SETF(len(buf)), buf, True))
    except OSError as e:
        print('  result:', e)
    for rep in drain(fd, 0.5):
        print('  reply: report', rep[0], rep[1:].hex(' '))
    after = snapshot(fd)
    for rid in before:
        lim = 0x400 if rid == 6 else len(before[rid])   # report 6 tail is volatile scratch
        diff = [i for i in range(lim) if before[rid][i] != after[rid][i]]
        if diff:
            print(f'  report {rid} changed at', [f'{i:#x}:{before[rid][i]:02x}->{after[rid][i]:02x}' for i in diff[:24]])
        if rid in (2, 3, 4) and any(after[rid]):
            print(f'  report {rid} now reads:', after[rid][:32].hex(' '))
    print('done')

if __name__ == '__main__':
    run(int(sys.argv[1]), bytes.fromhex(sys.argv[2] if len(sys.argv) > 2 else ''))
