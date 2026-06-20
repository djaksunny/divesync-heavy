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

# -------------------------
# Serial Connection
# -------------------------
def auto_connect():
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())

    if not ports:
        raise Exception("No serial ports found.")

    for p in ports:
        try:
            s = serial.Serial(p.device, 115200, timeout=1.0) # Increased timeout slightly for handshakes
            time.sleep(1)  # Allow device to reboot if needed
            return s
        except:
            continue

    raise Exception("No device responded")

try:
    ser = auto_connect()
except Exception as e:
    root_temp = tk.Tk()
    root_temp.withdraw()
    msgbox.showerror("Actuator UI Error", f"Could not connect to serial device:\n{e}")
    sys.exit()

# -------------------------
# State & Thread Safety Locks
# -------------------------
data_lock = threading.Lock()

# Shared variables (Protected by data_lock)
adc = 0.0
pwm = 0
setpoint = 100.0

# Default parameters
Kp = 1.0
Ki = 1.0
Kd = 0.05
amp = 1000.0
offset = 2000.0
period = 5.0
wave_type = "sine"

t0 = time.time()
wave_t = 0.0

# -------------------------
# PID Initialize
# -------------------------
pid = PID(Kp, Ki, Kd, setpoint=setpoint)
pid.output_limits = (-255, 255)
pid.sample_time = 0.01

# -------------------------
# Waveform Generator
# -------------------------
def waveform(dt):
    global wave_t
    wave_t += dt

    if wave_type == "sine":
        return offset + amp * math.sin(2 * math.pi * wave_t / period)
    elif wave_type == "square":
        return offset + (amp if (wave_t % period) < period / 2 else -amp)
    elif wave_type == "triangle":
        p = (wave_t % period) / period
        return offset + amp * (4 * abs(p - 0.5) - 1)
    return offset

# -------------------------
# Background Control Loop (STRICT HANDSHAKE)
# -------------------------
def control_loop():
    global adc, pwm, setpoint

    # 1. Give Arduino 2 seconds to finish its bootloader sequence
    time.sleep(2)
    
    try:
        # 2. Flush out any garbage data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # 3. KICKSTART THE HANDSHAKE
        # We send an initial command so the Arduino replies with its first ADC reading
        ser.write(b"0\n")
    except Exception as e:
        print(f"Failed to initialize handshake: {e}")
        return

    while True:
        try:
            # 4. Wait for Arduino's reply (Blocking read)
            line = ser.readline().decode(errors="ignore").strip()

            # 5. Parse the handshake response
            if line.startswith("I:"):
                try:
                    with data_lock:
                        adc = float(line[2:])
                except ValueError:
                    pass

            # 6. Time pacing
            dt = 0.01
            time.sleep(dt)

            # 7. Calculate next step under lock
            with data_lock:
                setpoint = waveform(dt)
                pid.setpoint = setpoint
                pid.Kp = Kp
                pid.Ki = Ki
                pid.Kd = Kd
                pwm = int(pid(adc))

            # 8. Send the next command (This prompts the Arduino to send the next 'I:' reading)
            ser.write(f"{pwm}\n".encode())

        except Exception as e:
            print(f"Loop Exception: {e}")
            break

# -------------------------
# GUI Layout Setup
# -------------------------
root = tk.Tk()
root.title("Actuator Control")

adc_var = tk.StringVar(value="0.0")
sp_var = tk.StringVar(value="100.0")
pwm_var = tk.StringVar(value="0")

main = ttk.Frame(root, padding=10)
main.pack(fill="both", expand=True)

left = ttk.Frame(main, padding=5)
left.pack(side="left", fill="y", padx=5)

right = ttk.Frame(main)
right.pack(side="right", fill="both", expand=True)

# Live Readouts
ttk.Label(left, text="--- Live Readings ---", font=('Helvetica', 10, 'bold')).pack(pady=5)
ttk.Label(left, text="ADC (Current Position):").pack(anchor="w")
ttk.Label(left, textvariable=adc_var, font=('Helvetica', 12, 'bold')).pack(anchor="w", pady=2)

ttk.Label(left, text="Setpoint (Target):").pack(anchor="w")
ttk.Label(left, textvariable=sp_var, font=('Helvetica', 12, 'bold')).pack(anchor="w", pady=2)

ttk.Label(left, text="PWM output:").pack(anchor="w")
ttk.Label(left, textvariable=pwm_var, font=('Helvetica', 12, 'bold')).pack(anchor="w", pady=2)

# Dynamic Controls Panel
ttk.Label(left, text="--- Tuning Parameters ---", font=('Helvetica', 10, 'bold')).pack(pady=10)

def update_parameters(event=None):
    global Kp, Ki, Kd, amp, offset, period, wave_type
    try:
        with data_lock:
            Kp = float(entry_kp.get())
            Ki = float(entry_ki.get())
            Kd = float(entry_kd.get())
            amp = float(entry_amp.get())
            offset = float(entry_offset.get())
            period = float(entry_period.get())
            wave_type = combo_wave.get()
    except ValueError:
        msgbox.showwarning("Input Error", "Please enter valid numbers.")

# Mapping parameters to their default variables
param_defaults = {
    "Kp": Kp, "Ki": Ki, "Kd": Kd, 
    "Amplitude": amp, "Offset": offset, "Period": period
}

entries = {}
for param, default_val in param_defaults.items():
    frame = ttk.Frame(left)
    frame.pack(fill="x", pady=2)
    ttk.Label(frame, text=f"{param}:", width=10).pack(side="left")
    
    ent = ttk.Entry(frame, width=8)
    ent.insert(0, str(default_val))
    ent.pack(side="right", expand=True, fill="x")
    
    # Auto-apply changes on Enter key
    ent.bind("<Return>", update_parameters)
    entries[param] = ent

entry_kp, entry_ki, entry_kd = entries["Kp"], entries["Ki"], entries["Kd"]
entry_amp, entry_offset, entry_period = entries["Amplitude"], entries["Offset"], entries["Period"]

frame_wave = ttk.Frame(left)
frame_wave.pack(fill="x", pady=2)
ttk.Label(frame_wave, text="Wave Type:", width=10).pack(side="left")

combo_wave = ttk.Combobox(frame_wave, values=["sine", "square", "triangle"], width=8, state="readonly")
combo_wave.set(wave_type)
combo_wave.pack(side="right", expand=True, fill="x")

# Auto-apply changes when combobox selection changes
combo_wave.bind("<<ComboboxSelected>>", update_parameters)

# -------------------------
# Matplotlib Plots Setup
# -------------------------
N = 200
t_buf, adc_buf, sp_buf, pwm_buf = [], [], [], []

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 5), sharex=True)
fig.tight_layout(pad=3.0)

line_adc, = ax1.plot([], [], label="ADC Actual", color="blue")
line_sp, = ax1.plot([], [], label="Setpoint", color="red", linestyle="--")
ax1.set_title("Position Tracking")
ax1.set_ylabel("Value")
ax1.legend(loc="upper right")
ax1.grid(True)

line_pwm, = ax2.plot([], [], label="PWM Effort", color="orange")
ax2.set_title("Control Effort")
ax2.set_xlabel("Time (s)")
ax2.set_ylabel("PWM Output")
ax2.legend(loc="upper right")
ax2.grid(True)

canvas = FigureCanvasTkAgg(fig, master=right)
canvas.get_tk_widget().pack(fill="both", expand=True)

# Adjust axes limits dynamically based on expected range
ax1.set_ylim(0, 4095)  # 12-bit ADC range
ax2.set_ylim(-260, 260)

# -------------------------
# Animation & Tkinter loop
# -------------------------
def animate(_):
    with data_lock:
        local_adc = adc
        local_sp = setpoint
        local_pwm = pwm

    now = time.time() - t0

    t_buf.append(now)
    adc_buf.append(local_adc)
    sp_buf.append(local_sp)
    pwm_buf.append(local_pwm)

    if len(t_buf) > N:
        t_buf.pop(0)
        adc_buf.pop(0)
        sp_buf.pop(0)
        pwm_buf.pop(0)

    line_adc.set_data(t_buf, adc_buf)
    line_sp.set_data(t_buf, sp_buf)
    line_pwm.set_data(t_buf, pwm_buf)

    if len(t_buf) > 1:
        ax1.set_xlim(t_buf[0], t_buf[-1])
        ax2.set_xlim(t_buf[0], t_buf[-1])

    adc_var.set(f"{local_adc:.1f}")
    sp_var.set(f"{local_sp:.1f}")
    pwm_var.set(f"{local_pwm}")

    return line_adc, line_sp, line_pwm

anim = FuncAnimation(fig, animate, interval=50, blit=False) 

# -------------------------
# Safe Thread Execution
# -------------------------
loop_thread = threading.Thread(target=control_loop, daemon=True)
loop_thread.start()

# -------------------------
# Application Cleanup
# -------------------------
def close():
    try:
        ser.write(b"0\n")  # Write safe neutral position
        ser.close()
    except:
        pass
    root.destroy()
    sys.exit()

root.protocol("WM_DELETE_WINDOW", close)
root.mainloop()