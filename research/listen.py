"""Passively log input reports from the vendor interface (read-only)."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import os, select, time, sys, hidio
dev = hidio.find_vendor_hidraw()
fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
end = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 120)
print('listening on', dev, flush=True)
while time.time() < end:
    r, _, _ = select.select([fd], [], [], 0.5)
    if r:
        data = os.read(fd, 4096)
        print(f'{time.strftime("%H:%M:%S")} report {data[0]}: {data[1:].hex(" ")}', flush=True)
print('done', flush=True)
