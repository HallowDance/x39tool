"""Poll lighting memory (read-only) and log every change, plus vendor events."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import os, select, time, sys, x39, hidio
m = x39.Mouse()
ev = os.open(hidio.find_vendor_hidraw(), os.O_RDONLY | os.O_NONBLOCK)
prev = m.read_memory(0x400, 0x480)
end = time.time() + float(sys.argv[1])
print('watching', flush=True)
while time.time() < end:
    while select.select([ev], [], [], 0)[0]:
        print(time.strftime('%H:%M:%S'), 'event', os.read(ev, 64).hex(' '), flush=True)
    cur = m.read_memory(0x400, 0x480)
    if cur != prev:
        d = [f'{0x400+i:#x}:{prev[i]:02x}->{cur[i]:02x}' for i in range(len(cur)) if cur[i] != prev[i]]
        print(time.strftime('%H:%M:%S'), 'changed', d, flush=True)
        prev = cur
    time.sleep(0.4)
print('done', flush=True)
