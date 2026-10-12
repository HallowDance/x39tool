#!/usr/bin/env python3
"""Simple GUI for the Temu X-39 Pro (36b7:fd13): DPI, lighting, button remapping, polling rate."""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
import x39

DPI_UNIT = 100  # raw level -> DPI (uncalibrated estimate)


class ButtonDialog(tk.Toplevel):
    """Pick a mouse action or a keyboard key (+ modifiers) for one button slot."""
    def __init__(self, master, title, code):
        super().__init__(master)
        self.title(title); self.resizable(False, False); self.result = None
        self.kind = tk.StringVar(value='key' if code[0] == x39.KEY_CODE else 'mouse')
        frm = ttk.Frame(self, padding=12); frm.pack(fill='both')

        ttk.Radiobutton(frm, text='Mouse / media action', variable=self.kind, value='mouse').grid(row=0, column=0, sticky='w')
        self.action = ttk.Combobox(frm, values=list(x39.MOUSE_ACTIONS), state='readonly', width=24)
        self.action.grid(row=0, column=1, columnspan=4, sticky='w', pady=2)
        current = x39.describe_button(code)
        self.action.set(current if current in x39.MOUSE_ACTIONS else 'Left click')

        ttk.Radiobutton(frm, text='Keyboard key', variable=self.kind, value='key').grid(row=1, column=0, sticky='w')
        self.key = ttk.Combobox(frm, values=list(x39.HID_KEYS), state='readonly', width=12)
        self.key.grid(row=1, column=1, sticky='w', pady=2)
        self.key.set(x39.HID_NAMES.get(code[2], 'a') if code[0] == x39.KEY_CODE else 'a')
        self.mods = {}
        for i, (name, bit) in enumerate(x39.MODIFIERS.items()):
            v = tk.BooleanVar(value=code[0] == x39.KEY_CODE and bool(code[1] & bit))
            ttk.Checkbutton(frm, text=name, variable=v).grid(row=2, column=1 + i, sticky='w')
            self.mods[name] = v

        btns = ttk.Frame(frm); btns.grid(row=3, column=0, columnspan=5, sticky='e', pady=(10, 0))
        ttk.Button(btns, text='Cancel', command=self.destroy).pack(side='right')
        ttk.Button(btns, text='OK', command=self.ok).pack(side='right', padx=6)
        self.transient(master); self.grab_set(); self.wait_window()

    def ok(self):
        if self.kind.get() == 'mouse':
            self.result = x39.MOUSE_ACTIONS[self.action.get()]
        else:
            self.result = x39.key_code(self.key.get(), [m for m, v in self.mods.items() if v.get()])
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('X-39 Pro Configurator'); self.resizable(False, False)
        self.mouse = x39.Mouse()
        self.backed_up = False

        top = ttk.Frame(self, padding=(12, 10)); top.pack(fill='x')
        ttk.Label(top, text='Edit profile').pack(side='left')
        self.profile = ttk.Combobox(top, values=[f'Profile {i + 1}' for i in range(5)], state='readonly', width=10)
        self.profile.pack(side='left', padx=(4, 16)); self.profile.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        ttk.Label(top, text='Active profile').pack(side='left')
        self.active = ttk.Combobox(top, values=[f'Profile {i + 1}' for i in range(5)], state='readonly', width=10)
        self.active.pack(side='left', padx=4)

        nb = ttk.Notebook(self); nb.pack(fill='both', padx=12)
        self.build_dpi(nb); self.build_lighting(nb); self.build_buttons(nb)

        bottom = ttk.Frame(self, padding=(12, 10)); bottom.pack(fill='x')
        ttk.Button(bottom, text='Apply to mouse', command=self.apply).pack(side='right')
        ttk.Button(bottom, text='Reload', command=self.load).pack(side='right', padx=6)
        ttk.Button(bottom, text='Exit', command=self.quit_app).pack(side='right', padx=(0, 18))
        ttk.Button(bottom, text='Restore backup…', command=self.restore).pack(side='left')
        self.status = ttk.Label(self, padding=(12, 0, 12, 10), foreground='gray'); self.status.pack(fill='x')
        self.protocol('WM_DELETE_WINDOW', self.quit_app)
        self.bind('<Control-q>', lambda e: self.quit_app())
        self.load()

    # ---------- tabs ----------
    def build_dpi(self, nb):
        f = ttk.Frame(nb, padding=12); nb.add(f, text='DPI')
        ttk.Label(f, text='Stage').grid(row=0, column=0); ttk.Label(f, text='On').grid(row=0, column=1)
        ttk.Label(f, text='Level (raw)').grid(row=0, column=2); ttk.Label(f, text='≈ DPI').grid(row=0, column=3)
        ttk.Label(f, text='Current').grid(row=0, column=4)
        self.stage_vars, self.cur_stage = [], tk.IntVar()
        for i in range(5):
            on, val = tk.BooleanVar(), tk.IntVar()
            est = ttk.Label(f, width=7)
            val.trace_add('write', lambda *a, v=val, l=est: l.config(text=self._est(v)))
            ttk.Label(f, text=str(i + 1)).grid(row=i + 1, column=0, padx=6)
            ttk.Checkbutton(f, variable=on).grid(row=i + 1, column=1)
            ttk.Spinbox(f, from_=1, to=160, textvariable=val, width=6).grid(row=i + 1, column=2, padx=6, pady=2)
            est.grid(row=i + 1, column=3)
            ttk.Radiobutton(f, variable=self.cur_stage, value=i).grid(row=i + 1, column=4)
            self.stage_vars.append((on, val))
        ttk.Label(f, text='Polling rate').grid(row=7, column=0, columnspan=2, sticky='w', pady=(12, 0))
        self.poll = ttk.Combobox(f, values=[f'{hz} Hz' for hz in x39.POLLING_RATES], state='readonly', width=9)
        self.poll.grid(row=7, column=2, columnspan=2, sticky='w', pady=(12, 0))

    def _est(self, var):
        try: return f'{var.get() * DPI_UNIT}'
        except tk.TclError: return '?'

    def build_lighting(self, nb):
        f = ttk.Frame(nb, padding=12); nb.add(f, text='Lighting')
        ttk.Label(f, text='Mode').grid(row=0, column=0, sticky='w')
        self.light_mode = ttk.Combobox(f, values=list(x39.LIGHT_MODES), state='readonly', width=18)
        self.light_mode.grid(row=0, column=1, sticky='w', pady=3)
        ttk.Label(f, text='Colour').grid(row=1, column=0, sticky='w')
        self.color_btn = tk.Button(f, width=6, relief='groove', command=self.pick_color)
        self.color_btn.grid(row=1, column=1, sticky='w', pady=3)
        self.color = (255, 0, 0)
        # The firmware's speed byte runs 1 = fastest .. 8 = slowest; shown here as slow -> fast.
        # Brightness: 0 = off, 1-3 = dim..bright; values above 3 look the same as 3 (tested on the mouse).
        ttk.Label(f, text='Brightness').grid(row=3, column=0, sticky='w')
        br = ttk.Frame(f); br.grid(row=3, column=1, sticky='w', pady=3)
        ttk.Label(br, text='dim').pack(side='left')
        self.bright = tk.IntVar()
        tk.Scale(br, from_=1, to=3, orient='horizontal', variable=self.bright, showvalue=False, length=140).pack(side='left', padx=4)
        ttk.Label(br, text='bright').pack(side='left')
        ttk.Label(f, text='Speed').grid(row=2, column=0, sticky='w')
        sp = ttk.Frame(f); sp.grid(row=2, column=1, sticky='w', pady=3)
        ttk.Label(sp, text='slow').pack(side='left')
        self.speed = tk.IntVar()
        tk.Scale(sp, from_=1, to=8, orient='horizontal', variable=self.speed, showvalue=False, length=140).pack(side='left', padx=4)
        ttk.Label(sp, text='fast').pack(side='left')

    def pick_color(self):
        c = colorchooser.askcolor(color='#%02x%02x%02x' % self.color, parent=self)[0]
        if c:
            self.color = tuple(int(x) for x in c); self._show_color()

    def _show_color(self):
        hexc = '#%02x%02x%02x' % self.color
        self.color_btn.config(bg=hexc, activebackground=hexc)

    def build_buttons(self, nb):
        f = ttk.Frame(nb, padding=12); nb.add(f, text='Buttons')
        self.button_labels = {}
        for row, (slot, name) in enumerate(x39.BUTTON_SLOTS):
            col = 0 if row < 11 else 3; r = row % 11
            ttk.Label(f, text=name).grid(row=r, column=col, sticky='w', padx=(0 if col == 0 else 18, 6))
            lbl = ttk.Label(f, width=18, relief='sunken', padding=(4, 1)); lbl.grid(row=r, column=col + 1, pady=1)
            b = ttk.Button(f, text='…', width=2, command=lambda s=slot, n=name: self.edit_button(s, n))
            b.grid(row=r, column=col + 2)
            if slot == 0:
                b.state(['disabled'])  # never remap left click away: avoids locking yourself out
            self.button_labels[slot] = lbl
        self.pending_buttons = {}

    def edit_button(self, slot, name):
        p = self.profile.current()
        d = ButtonDialog(self, name, self.pending_buttons.get((p, slot), self.cfg.button(p, slot)))
        if d.result:
            self.pending_buttons[(p, slot)] = d.result
            self.button_labels[slot].config(text=x39.describe_button(d.result) + ' *')

    # ---------- data ----------
    def load(self):
        try:
            self.mem = self.mouse.read_memory()
        except Exception as e:
            messagebox.showerror('Read failed', str(e)); return
        self.cfg = x39.Config(self.mem)
        self.pending_buttons = {}
        if self.profile.current() < 0:
            self.profile.current(self.cfg.active_profile)
        self.active.current(self.cfg.active_profile)
        self.refresh()
        self.set_status('Loaded settings from mouse.')

    def refresh(self):
        p = self.profile.current()
        for (on, val), (en, x, _y) in zip(self.stage_vars, self.cfg.dpi_stages(p)):
            on.set(en); val.set(x)
        self.cur_stage.set(self.cfg.current_stage(p))
        self.poll.set(f'{self.cfg.polling(p)} Hz')
        l = self.cfg.lighting(p)
        self.light_mode.set(l['mode']); self.color = l['color']; self._show_color()
        self.speed.set(9 - min(max(l['speed'], 1), 8)); self.bright.set(min(max(l['brightness'], 1), 3))
        for slot, lbl in self.button_labels.items():
            code = self.pending_buttons.get((p, slot), self.cfg.button(p, slot))
            lbl.config(text=x39.describe_button(code) + (' *' if (p, slot) in self.pending_buttons else ''))

    def collect(self):
        """Edits on screen (current profile) + pending button edits -> new memory image."""
        new = x39.Config(self.mem); p = self.profile.current()
        stages = [(on.get(), val.get()) for on, val in self.stage_vars]
        if not any(on for on, _ in stages): raise ValueError('At least one DPI stage must be on.')
        if not stages[self.cur_stage.get()][0]: raise ValueError('The current DPI stage must be switched on.')
        for i, (on, val) in enumerate(stages):
            if not 1 <= val <= 160: raise ValueError(f'DPI level for stage {i + 1} must be 1–160.')
            new.set_dpi_stage(p, i, on, val)
        new.set_current_stage(p, self.cur_stage.get())
        new.set_polling(p, int(self.poll.get().split()[0]))
        if self.light_mode.get() in x39.LIGHT_MODES:
            new.set_lighting(p, mode=self.light_mode.get())
        new.set_lighting(p, color=self.color, speed=9 - self.speed.get(), brightness=self.bright.get())
        for (bp, slot), code in self.pending_buttons.items():
            new.set_button(bp, slot, code)
        new.active_profile = self.active.current()
        return bytes(new.mem)

    def apply(self):
        try:
            new = self.collect()
        except (ValueError, tk.TclError) as e:
            messagebox.showerror('Invalid setting', str(e)); return
        if new == self.mem:
            self.set_status('Nothing changed.'); return
        try:
            if not self.backed_up:
                x39.backup(self.mem, 'before-gui'); self.backed_up = True
            n = self.mouse.write_changes(self.mem, new)
            if new[x39.ACTIVE_PROFILE] != self.mem[x39.ACTIVE_PROFILE]:
                self.mouse.apply_profile_switch()
        except Exception as e:
            messagebox.showerror('Write failed', f'{e}\n\nUse "Restore backup…" if the mouse misbehaves.'); return
        self.load(); self.set_status(f'Applied ({n} write{"s" * (n != 1)}, verified).')

    def restore(self):
        path = filedialog.askopenfilename(parent=self, initialdir=x39.BACKUP_DIR, title='Restore backup',
                                          filetypes=[('Backups', '*.bin')])
        if not path: return
        data = open(path, 'rb').read()
        if len(data) < x39.MEM_SIZE:
            messagebox.showerror('Restore', 'Not a full settings backup (made by this tool).'); return
        if not messagebox.askyesno('Restore', f'Write {path.split("/")[-1]} to the mouse?'): return
        try:
            n = self.mouse.write_changes(self.mem, data[:x39.MEM_SIZE])
        except Exception as e:
            messagebox.showerror('Restore failed', str(e)); return
        self.load(); self.set_status(f'Restored backup ({n} writes, verified).')

    def set_status(self, text):
        self.status.config(text=text)

    def quit_app(self):
        try:
            unsaved = self.collect() != self.mem
        except (ValueError, tk.TclError):
            unsaved = True
        if unsaved and not messagebox.askyesno('Exit', 'You have changes that are not applied to the mouse.\nExit anyway?'):
            return
        self.mouse.close()
        self.destroy()


if __name__ == '__main__':
    App().mainloop()
