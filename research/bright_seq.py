"""Play a sequence of brightness values with on-screen labels, then restore."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sys, time, subprocess, x39
seq, dt = [int(v) for v in sys.argv[1].split(',')], float(sys.argv[2])
m = x39.Mouse(); c = x39.Config(m.read_memory())
addr = x39.LIGHTING[c.active_profile] + 7; orig = c.mem[addr]
def setb(v):
    m._start(); m._send(bytes([0xf3, addr & 0xff, addr >> 8, 1, 0, 0, 0, v])); m._send(b'\xf5\x01')
def show(text):
    subprocess.run(['dunstify', '-r', '3939', '-t', str(int(dt * 1000) + 500), 'Mouse brightness', text])
show('starting in 5 s…'); time.sleep(5)
try:
    for v in seq:
        setb(v); show(f'level {v}'); print(time.strftime('%H:%M:%S'), 'brightness', v, flush=True); time.sleep(dt)
finally:
    setb(orig); m._start(); r = m._read8(addr, 1)[0]
    show(f'done, restored to {r}'); print('restored', r, flush=True)
