import sys
import serial
import time
import threading
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as msgbox
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
from simple_pid import PID

# ─────────────────────────────────────────────────────────────
# Serial connection
# ─────────────────────────────────────────────────────────────
def auto_connect():
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        try:
            s = serial.Serial(p.device, 115200, timeout=1.0)
            time.sleep(1)
            return s
        except:
            continue
    raise Exception("No device responded")

try:
    ser = auto_connect()
except Exception as e:
    root_temp = tk.Tk()
    root_temp.withdraw()
    msgbox.showerror("Actuator UI Error", f"Could not connect:\n{e}")
    sys.exit()

# ─────────────────────────────────────────────────────────────
# Shared state  (all writes must hold data_lock)
# ─────────────────────────────────────────────────────────────
data_lock = threading.Lock()

# Telemetry
adc         = 0.0
depth       = 0.0
pressure    = 0.0
temperature = 0.0
battery_v   = 0.0
depth_ok    = False
pwm         = 0

# Setpoints published each cycle (used by plots + sidebar)
pos_setpoint   = 2000.0   # ADC counts – inner loop reference
depth_setpoint = 0.0      # metres    – outer loop reference (NaN in position mode)

# Control mode
control_mode = "position"   # "position" | "depth"

# ── Position PID tuning ──
Kp,   Ki,   Kd   = 1.0,    1.0,   0.05

# ── Depth PID tuning (outer loop; output → pos_setpoint) ──
Kp_d, Ki_d, Kd_d = 1000.0, 0.0,   50.0

# ── Position waveform (ADC counts) ──
pos_amp, pos_offset, pos_period = 1000.0, 2000.0, 10.0

# ── Depth waveform (metres) ──
dep_amp, dep_offset, dep_period = 0.2,    0.5,    20.0

# Shared wave shape
wave_type = "square"
wave_t    = 0.0
t0        = time.time()

# ─────────────────────────────────────────────────────────────
# PID objects
# ─────────────────────────────────────────────────────────────
pos_pid = PID(Kp,   Ki,   Kd,   setpoint=pos_setpoint)
pos_pid.output_limits = (-255, 255)
pos_pid.sample_time   = 0.01

dep_pid = PID(Kp_d, Ki_d, Kd_d, setpoint=0.0)
dep_pid.output_limits = (50, 4050)    # clamp output to actuator ADC range
dep_pid.sample_time   = 0.01

def _reset_pid(pid_obj):
    """Zero integral and clear derivative history (bumpless-ish transfer)."""
    pid_obj._integral    = 0.0
    pid_obj._last_input  = None
    pid_obj._last_output = None

# ─────────────────────────────────────────────────────────────
# Waveform  (shared wave_t; separate amp/offset/period per mode)
# ─────────────────────────────────────────────────────────────
def waveform(t, amplitude, offset_val, period):
    if wave_type == "sine":
        return offset_val + amplitude * math.sin(2 * math.pi * t / period)
    elif wave_type == "square":
        return offset_val + (amplitude if (t % period) < period / 2 else -amplitude)
    elif wave_type == "triangle":
        p = (t % period) / period
        return offset_val + amplitude * (4 * abs(p - 0.5) - 1)
    return offset_val

# ─────────────────────────────────────────────────────────────
# Telemetry  (8-field CSV from firmware)
# time_ms, actuator_raw, motor_cmd, depth_m, pressure_mbar, temp_c, depth_ok, battery_v
# ─────────────────────────────────────────────────────────────
def parse_telemetry(line):
    parts = line.split(",")
    if len(parts) != 8:
        return None
    try:
        return {
            "time_ms":       int(parts[0].strip()),
            "actuator_raw":  int(parts[1].strip()),
            "motor_cmd":     int(parts[2].strip()),
            "depth_m":       float(parts[3].strip()),   # may be nan
            "pressure_mbar": float(parts[4].strip()),
            "temp_c":        float(parts[5].strip()),
            "depth_ok":      bool(int(parts[6].strip())),
            "battery_v":     float(parts[7].strip()),
        }
    except (ValueError, IndexError):
        return None

def send_command(u):
    ser.write(f"U:{int(max(-255, min(255, u)))}\n".encode())

# ─────────────────────────────────────────────────────────────
# Control loop
# ─────────────────────────────────────────────────────────────
def control_loop():
    global adc, depth, pressure, temperature, battery_v, depth_ok
    global pwm, pos_setpoint, depth_setpoint, wave_t

    time.sleep(2)                   # wait for device boot
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    last_t = time.time()

    while True:
        try:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue

            # ACK / ERR / status lines from firmware – skip, just log
            if not raw[0].isdigit():
                print(f"[DEVICE] {raw}")
                continue

            telem = parse_telemetry(raw)
            if telem is None:
                print(f"[BAD LINE] {raw}")
                continue

            now    = time.time()
            dt     = now - last_t
            last_t = now

            with data_lock:
                # ── Ingest telemetry ──
                adc         = telem["actuator_raw"]
                depth       = telem["depth_m"]
                pressure    = telem["pressure_mbar"]
                temperature = telem["temp_c"]
                battery_v   = telem["battery_v"]
                depth_ok    = telem["depth_ok"]

                wave_t += dt

                # ── Push latest gains to PID objects ──
                pos_pid.Kp = Kp;   pos_pid.Ki = Ki;   pos_pid.Kd = Kd
                dep_pid.Kp = Kp_d; dep_pid.Ki = Ki_d; dep_pid.Kd = Kd_d

                # ─────────────────────────────────────
                #  MODE: depth cascade
                #    outer: depth error  → position SP
                #    inner: position error → PWM
                # ─────────────────────────────────────
                if control_mode == "depth" and depth_ok and not math.isnan(depth):
                    depth_setpoint   = waveform(wave_t, dep_amp, dep_offset, dep_period)
                    dep_pid.setpoint = depth_setpoint
                    pos_sp           = float(dep_pid(depth))   # outer output → inner ref
                    pos_setpoint     = pos_sp
                    pos_pid.setpoint = pos_setpoint
                    pwm              = int(pos_pid(adc))

                # ─────────────────────────────────────
                #  MODE: depth requested but sensor down
                #    → hold last pos_setpoint, inner loop only
                # ─────────────────────────────────────
                elif control_mode == "depth":
                    depth_setpoint   = float("nan")
                    pos_pid.setpoint = pos_setpoint     # unchanged
                    pwm              = int(pos_pid(adc))

                # ─────────────────────────────────────
                #  MODE: position only
                # ─────────────────────────────────────
                else:
                    pos_setpoint     = waveform(wave_t, pos_amp, pos_offset, pos_period)
                    depth_setpoint   = float("nan")
                    pos_pid.setpoint = pos_setpoint
                    pwm              = int(pos_pid(adc))

            send_command(pwm)

        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            break

# ─────────────────────────────────────────────────────────────
# GUI  –  root + layout
# ─────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Actuator + Depth Cascade Control")

# ── StringVars ──
sv_adc      = tk.StringVar(value="0.0")
sv_pos_sp   = tk.StringVar(value="2000.0")
sv_dep_sp   = tk.StringVar(value="---")
sv_pwm      = tk.StringVar(value="0")
sv_depth    = tk.StringVar(value="0.000")
sv_pressure = tk.StringVar(value="0.0")
sv_temp     = tk.StringVar(value="0.0")
sv_batt     = tk.StringVar(value="0.00")
sv_dok      = tk.StringVar(value="--")
sv_mode     = tk.StringVar(value="position")

main = ttk.Frame(root, padding=10)
main.pack(fill="both", expand=True)

# ── Scrollable sidebar ──
left_outer = ttk.Frame(main)
left_outer.pack(side="left", fill="y")

_cv = tk.Canvas(left_outer, width=210, highlightthickness=0)
_sb = ttk.Scrollbar(left_outer, orient="vertical", command=_cv.yview)
left = ttk.Frame(_cv, padding=5)
left.bind("<Configure>", lambda e: _cv.configure(scrollregion=_cv.bbox("all")))
_cv.create_window((0, 0), window=left, anchor="nw")
_cv.configure(yscrollcommand=_sb.set)
_cv.pack(side="left", fill="y")
_sb.pack(side="right", fill="y")

def _scroll(event):
    _cv.yview_scroll(int(-1 * (event.delta / 120)), "units")
_cv.bind_all("<MouseWheel>", _scroll)

right = ttk.Frame(main)
right.pack(side="right", fill="both", expand=True)

# ── Layout helpers ──
def _section(text):
    ttk.Label(left, text=text, font=('Helvetica', 9, 'bold')).pack(pady=(8, 1), anchor="w")
    ttk.Separator(left, orient="horizontal").pack(fill="x")

def _readout(label, var, size=11, color=None):
    ttk.Label(left, text=label, font=('Helvetica', 8)).pack(anchor="w")
    kw = dict(textvariable=var, font=('Helvetica', size, 'bold'))
    if color:
        kw["foreground"] = color
    ttk.Label(left, **kw).pack(anchor="w", pady=1)

def _param(label, default, callback):
    f = ttk.Frame(left)
    f.pack(fill="x", pady=1)
    ttk.Label(f, text=label, width=13, font=('Helvetica', 8)).pack(side="left")
    e = ttk.Entry(f, width=8)
    e.insert(0, str(default))
    e.pack(side="right", expand=True, fill="x")
    e.bind("<Return>", callback)
    return e

def _note(text):
    ttk.Label(left, text=text, font=('Helvetica', 7, 'italic'),
              foreground="gray").pack(anchor="w")

# ─────────────────────────────────────────────────────────────
# Sidebar – Live Readings
# ─────────────────────────────────────────────────────────────
_section("Live Readings")
_readout("ADC (Position):",    sv_adc,      size=11)
_readout("Position SP (ADC):", sv_pos_sp,   size=11)
_readout("Depth SP (m):",      sv_dep_sp,   size=11, color="darkgreen")
_readout("PWM Output:",        sv_pwm,      size=11)
_readout("Depth (m):",         sv_depth,    size=12, color="darkgreen")
_readout("Pressure (mbar):",   sv_pressure, size=10)
_readout("Temperature (°C):",  sv_temp,     size=10)
_readout("Battery (V):",       sv_batt,     size=11, color="darkblue")

ttk.Label(left, text="Depth Sensor:", font=('Helvetica', 8)).pack(anchor="w")
_dok_lbl = tk.Label(left, textvariable=sv_dok, font=('Helvetica', 10, 'bold'))
_dok_lbl.pack(anchor="w", pady=1)

ttk.Button(left, text="⏹  STOP",
           command=lambda: ser.write(b"S\n")).pack(fill="x", pady=6)

# ─────────────────────────────────────────────────────────────
# Sidebar – Control Mode
# ─────────────────────────────────────────────────────────────
_section("Control Mode")

def on_mode_change():
    global control_mode
    new = sv_mode.get()
    with data_lock:
        if new == "depth":
            _reset_pid(dep_pid)    # clear depth integrator before engaging outer loop
        else:
            _reset_pid(pos_pid)    # clear position integrator on re-engagement
        control_mode = new

ttk.Radiobutton(left, text="Position only",  variable=sv_mode,
                value="position", command=on_mode_change).pack(anchor="w")
ttk.Radiobutton(left, text="Depth cascade",  variable=sv_mode,
                value="depth",    command=on_mode_change).pack(anchor="w")
_note("Cascade: depth PID → pos SP → pos PID → PWM")
_note("Falls back to holding position if sensor fails")

# ─────────────────────────────────────────────────────────────
# Sidebar – Position PID
# ─────────────────────────────────────────────────────────────
_section("Position PID  (inner loop)")
_note("Output: PWM  [-255 … 255]")

def _upd_pos_pid(event=None):
    global Kp, Ki, Kd
    try:
        with data_lock:
            Kp = float(e_kp.get())
            Ki = float(e_ki.get())
            Kd = float(e_kd.get())
    except ValueError:
        msgbox.showwarning("Input Error", "Enter valid numbers.")

e_kp = _param("Kp:", Kp, _upd_pos_pid)
e_ki = _param("Ki:", Ki, _upd_pos_pid)
e_kd = _param("Kd:", Kd, _upd_pos_pid)

# ─────────────────────────────────────────────────────────────
# Sidebar – Position Waveform
# ─────────────────────────────────────────────────────────────
_section("Position Waveform")
_note("Active in 'position only' mode")
_note("Units: ADC counts  [0 … 4095]")

def _upd_pos_wave(event=None):
    global pos_amp, pos_offset, pos_period, wave_type
    try:
        with data_lock:
            pos_amp    = float(e_pa.get())
            pos_offset = float(e_po.get())
            pos_period = float(e_pp.get())
            wave_type  = cb_wave.get()
    except ValueError:
        msgbox.showwarning("Input Error", "Enter valid numbers.")

e_pa = _param("Amplitude:", pos_amp,    _upd_pos_wave)
e_po = _param("Offset:",    pos_offset, _upd_pos_wave)
e_pp = _param("Period (s):", pos_period, _upd_pos_wave)

_fw = ttk.Frame(left)
_fw.pack(fill="x", pady=1)
ttk.Label(_fw, text="Wave shape:", width=13, font=('Helvetica', 8)).pack(side="left")
cb_wave = ttk.Combobox(_fw, values=["sine", "square", "triangle"], width=8, state="readonly")
cb_wave.set(wave_type)
cb_wave.pack(side="right", expand=True, fill="x")
cb_wave.bind("<<ComboboxSelected>>", _upd_pos_wave)

# ─────────────────────────────────────────────────────────────
# Sidebar – Depth PID  (outer loop)
# ─────────────────────────────────────────────────────────────
_section("Depth PID  (outer loop)")
_note("Output: position setpoint  [50 … 4050 ADC]")
_note("Tune Kp first with Ki=0, Kd=0")

def _upd_dep_pid(event=None):
    global Kp_d, Ki_d, Kd_d
    try:
        with data_lock:
            Kp_d = float(e_kpd.get())
            Ki_d = float(e_kid.get())
            Kd_d = float(e_kdd.get())
    except ValueError:
        msgbox.showwarning("Input Error", "Enter valid numbers.")

e_kpd = _param("Kp:", Kp_d, _upd_dep_pid)
e_kid = _param("Ki:", Ki_d, _upd_dep_pid)
e_kdd = _param("Kd:", Kd_d, _upd_dep_pid)

# ─────────────────────────────────────────────────────────────
# Sidebar – Depth Waveform  (outer loop reference)
# ─────────────────────────────────────────────────────────────
_section("Depth Waveform")
_note("Active in 'depth cascade' mode")
_note("Units: metres  (same wave shape as above)")

def _upd_dep_wave(event=None):
    global dep_amp, dep_offset, dep_period
    try:
        with data_lock:
            dep_amp    = float(e_da.get())
            dep_offset = float(e_do.get())
            dep_period = float(e_dp.get())
    except ValueError:
        msgbox.showwarning("Input Error", "Enter valid numbers.")

e_da = _param("Amplitude:", dep_amp,    _upd_dep_wave)
e_do = _param("Offset:",    dep_offset, _upd_dep_wave)
e_dp = _param("Period (s):", dep_period, _upd_dep_wave)

# ─────────────────────────────────────────────────────────────
# Plots
# ─────────────────────────────────────────────────────────────
N = 200
t_buf, adc_buf, pos_sp_buf = [], [], []
dep_sp_buf, pwm_buf, depth_buf = [], [], []

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(6, 7), sharex=True)
fig.tight_layout(pad=2.5)

# Plot 1 — Inner loop: position tracking
line_adc,    = ax1.plot([], [], label="ADC Actual",  color="blue")
line_pos_sp, = ax1.plot([], [], label="Position SP", color="red", linestyle="--")
ax1.set_title("Position Tracking  (inner loop)")
ax1.set_ylabel("ADC Value")
ax1.legend(loc="upper right", fontsize=7)
ax1.grid(True)
ax1.set_ylim(0, 4095)

# Plot 2 — Control effort
line_pwm, = ax2.plot([], [], label="PWM Effort", color="orange")
ax2.set_title("Control Effort")
ax2.set_ylabel("PWM Output")
ax2.legend(loc="upper right", fontsize=7)
ax2.grid(True)
ax2.set_ylim(-260, 260)

# Plot 3 — Outer loop: depth tracking
line_depth,  = ax3.plot([], [], label="Depth (m)",  color="green")
line_dep_sp, = ax3.plot([], [], label="Depth SP",   color="darkgreen", linestyle="--")
ax3.set_title("Depth Profile  (outer loop)")
ax3.set_xlabel("Time (s)")
ax3.set_ylabel("Depth (m)")
ax3.legend(loc="upper right", fontsize=7)
ax3.grid(True)

canvas_plot = FigureCanvasTkAgg(fig, master=right)
canvas_plot.get_tk_widget().pack(fill="both", expand=True)

# ─────────────────────────────────────────────────────────────
# Animation
# ─────────────────────────────────────────────────────────────
def animate(_):
    with data_lock:
        la  = adc
        lps = pos_setpoint
        lds = depth_setpoint
        lp  = pwm
        ld  = depth
        lpr = pressure
        lt  = temperature
        lb  = battery_v
        lok = depth_ok
        lm  = control_mode

    now = time.time() - t0
    t_buf.append(now);      adc_buf.append(la)
    pos_sp_buf.append(lps); dep_sp_buf.append(lds)
    pwm_buf.append(lp);     depth_buf.append(ld)

    if len(t_buf) > N:
        t_buf.pop(0);       adc_buf.pop(0)
        pos_sp_buf.pop(0);  dep_sp_buf.pop(0)
        pwm_buf.pop(0);     depth_buf.pop(0)

    line_adc.set_data(t_buf,    adc_buf)
    line_pos_sp.set_data(t_buf, pos_sp_buf)
    line_pwm.set_data(t_buf,    pwm_buf)
    line_depth.set_data(t_buf,  depth_buf)
    line_dep_sp.set_data(t_buf, dep_sp_buf)

    # Depth SP dashed line visible only in cascade mode
    line_dep_sp.set_visible(lm == "depth")

    if len(t_buf) > 1:
        ax1.set_xlim(t_buf[0], t_buf[-1])
        ax2.set_xlim(t_buf[0], t_buf[-1])
        ax3.set_xlim(t_buf[0], t_buf[-1])
        ax3.relim()
        ax3.autoscale_view(scalex=False, scaley=True)

    def _fmt(v, dec=3):
        return f"{v:.{dec}f}" if not math.isnan(v) else "---"

    sv_adc.set(f"{la:.1f}")
    sv_pos_sp.set(f"{lps:.1f}")
    sv_dep_sp.set(f"{_fmt(lds)} m" if not math.isnan(lds) else "---")
    sv_pwm.set(str(lp))
    sv_depth.set(_fmt(ld))
    sv_pressure.set(_fmt(lpr, 1))
    sv_temp.set(_fmt(lt, 1))
    sv_batt.set(f"{_fmt(lb, 2)} V")

    if lok:
        sv_dok.set("OK  ✓");   _dok_lbl.config(foreground="green")
    else:
        sv_dok.set("FAIL  ✗"); _dok_lbl.config(foreground="red")

    return line_adc, line_pos_sp, line_pwm, line_depth, line_dep_sp

anim = FuncAnimation(fig, animate, interval=50, blit=False)

# ─────────────────────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────────────────────
threading.Thread(target=control_loop, daemon=True).start()

def _close():
    try:
        ser.write(b"S\n")
        time.sleep(0.1)
        ser.close()
    except:
        pass
    root.destroy()
    sys.exit()

root.protocol("WM_DELETE_WINDOW", _close)
root.mainloop()
