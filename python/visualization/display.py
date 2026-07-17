import tkinter as tk
import ctypes
import sys

# --- Palette -----------------------------------------------------------
BG = "#0b0f14"          # window background
CARD_BG = "#121821"     # card background
BORDER = "#1f2a37"      # card border / dividers
FG_MUTED = "#5b6b7d"    # labels / captions
FG_PRIMARY = "#e6edf3"  # main readout values
ACCENT = "#3ba7ff"      # depth accent
ACCENT_2 = "#8b5cf6"    # setpoint accent
ACCENT_ACT = "#14b8a6"  # actuator accent (teal)
OK = "#2ecc71"          # error small -> good
WARN = "#f5b942"        # error medium -> caution
BAD = "#ff5d5d"         # error large -> off target

MONO = ("Consolas", 30, "bold")
MONO_SMALL = ("Consolas", 12)
LABEL_FONT = ("Segoe UI", 11, "bold")
TITLE_FONT = ("Segoe UI", 13, "bold")

ERROR_WARN_THRESHOLD = 0.1   # meters
ERROR_BAD_THRESHOLD = 0.3    # meters


class DepthDisplay:
    def __init__(self):
        self.closed = False

        self.root = tk.Tk()
        self.root.title("DiveSync Heavy Depth Control")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Apply dark mode theme to the main window title bar
        self._enable_dark_titlebar(self.root)

        # ---- Header ----
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 6))

        tk.Label(
            header, text="DIVESYNC", font=TITLE_FONT, bg=BG, fg=FG_PRIMARY
        ).pack(side="left")
        tk.Label(
            header, text="  •  DEPTH CONTROL", font=("Segoe UI", 13),
            bg=BG, fg=FG_MUTED
        ).pack(side="left")

        self.status_dot = tk.Canvas(
            header, width=12, height=12, bg=BG, highlightthickness=0
        )
        self.status_dot.pack(side="right", pady=2)
        self._dot_id = self.status_dot.create_oval(1, 1, 11, 11, fill=OK, outline="")

        # ---- Body: four cards ----
        body = tk.Frame(self.root, bg=BG)
        body.pack(padx=20, pady=(6, 20))

        self.depth_value = self._make_card(
            body, col=0, title="DEPTH", unit="m", accent=ACCENT
        )
        self.setpoint_value = self._make_card(
            body, col=1, title="SETPOINT", unit="m", accent=ACCENT_2
        )
        self.error_value = self._make_card(
            body, col=2, title="ERROR", unit="m", accent=FG_PRIMARY
        )
        self.actuator_value = self._make_card(
            body, col=3, title="ACTUATOR", unit="mm", accent=ACCENT_ACT
        )

        self.root.protocol("WM_DELETE_WINDOW", self._close)

        # draw window once
        self.root.update()

    @staticmethod
    def _enable_dark_titlebar(window):
        if sys.platform != "win32":
            return
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            rendering_policy = ctypes.c_int(1)
            
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy)
                )
                if result == 0:
                    break
        except Exception:
            pass

    def _make_card(self, parent, col, title, unit, accent):
        card = tk.Frame(
            parent, bg=CARD_BG, highlightbackground=BORDER,
            highlightthickness=1, bd=0
        )
        card.grid(row=0, column=col, padx=6)

        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(padx=22, pady=16)

        # accent tick
        tk.Frame(inner, bg=accent, width=28, height=3).pack(anchor="w", pady=(0, 8))

        tk.Label(
            inner, text=title, font=LABEL_FONT, bg=CARD_BG, fg=FG_MUTED
        ).pack(anchor="w")

        value_row = tk.Frame(inner, bg=CARD_BG)
        value_row.pack(anchor="w", pady=(2, 0))

        value_label = tk.Label(
            value_row, text="---", font=MONO, bg=CARD_BG, fg=FG_PRIMARY
        )
        value_label.pack(side="left")

        tk.Label(
            value_row, text=f" {unit}", font=MONO_SMALL, bg=CARD_BG, fg=FG_MUTED
        ).pack(side="left", padx=(4, 0), pady=(14, 0))

        return value_label

    def _close(self):
        self.closed = True
        self.root.destroy()

    def update(self, depth, setpoint, actuator_mm):
        if self.closed:
            return

        # process pending tkinter events
        self.root.update()

        # check if closed during update
        if self.closed:
            return

        if depth is not None:
            self.depth_value.config(text=f"{depth:.3f}")

        if setpoint is not None:
            self.setpoint_value.config(text=f"{setpoint:.3f}")
            
        if actuator_mm is not None:
            self.actuator_value.config(text=f"{actuator_mm:.1f}")
        else:
            self.actuator_value.config(text="---")

        if depth is not None and setpoint is not None:
            error = setpoint - depth
            self.error_value.config(text=f"{error:+.3f}")

            abs_err = abs(error)
            if abs_err <= ERROR_WARN_THRESHOLD:
                color = OK
            elif abs_err <= ERROR_BAD_THRESHOLD:
                color = WARN
            else:
                color = BAD
            self.error_value.config(fg=color)
            self.status_dot.itemconfig(self._dot_id, fill=color)
        else:
            self.error_value.config(text="---", fg=FG_PRIMARY)
            self.status_dot.itemconfig(self._dot_id, fill=FG_MUTED)

        self.root.update_idletasks()

    def close(self):
        if not self.closed:
            self.closed = True
            self.root.destroy()


if __name__ == "__main__":
    import math
    import time

    disp = DepthDisplay()
    t = 0.0
    while not disp.closed:
        depth = 0.5 + 0.2 * math.sin(5 * t)
        setpoint = 0.5 + 0.2 * math.cos(2 * t)
        # Mock actuator calculation moving with error dynamics
        sim_actuator = 50.0 + (setpoint - depth) * 100.0
        
        disp.update(depth, setpoint, sim_actuator)
        time.sleep(0.05)
        t += 0.05
