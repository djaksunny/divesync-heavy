import random

# Core
from core.experiment import Experiment
from core.serial_manager import SerialManager
from core.logger import Logger
from core.telemetry import Telemetry
from core.processor import Processor

# Controllers
from controllers.manual import ManualController
from controllers.pid import PIDController
from controllers.waveform import SquareWaveController
from controllers.inner import InnerPIDController

# Visualization
from visualization.plotter import Plotter
from visualization.display import DepthDisplay

# Config
BATTERY_CUTOFF_V      = 10.0
ACTUATOR_STROKE       = 50.0
ACTUATOR_EQUILIBRIUM  = 20.0
DEPTH_WAVE_LOW        = 0.5
DEPTH_WAVE_HIGH       = 0.5
DEPTH_WAVE_PERIOD     = 20.0

# Setup
exp = Experiment()
exp.setup_experiment()

if exp.com_port is None:
    print("No COM port selected. Exiting.")
    exit()

ser = SerialManager(exp.com_port)
log = Logger(exp.get_folder_path())
tel = Telemetry()
pro = Processor(ACTUATOR_STROKE)
ddp = DepthDisplay()

inn = InnerPIDController((4, 1.2, 0.3), 130)
depth_wave = None
depth_setpoint = None

match exp.mode:
    case "manual":
        con = ManualController(ACTUATOR_STROKE, ACTUATOR_EQUILIBRIUM)
    case "pid":
        con        = PIDController(ACTUATOR_STROKE, ACTUATOR_EQUILIBRIUM, (2, 1, 5))
        depth_wave = SquareWaveController(DEPTH_WAVE_LOW, DEPTH_WAVE_HIGH, DEPTH_WAVE_PERIOD)
    case "sysid":
        con = SquareWaveController(5, 45, 20)
    case _:
        print("Invalid or unsupported controller mode")
        exit()

print("\n=== WAITING FOR DEVICE READY ===\n")

while not exp.is_ready():
    line = ser.read_line()
    exp.handshake_protocol(line)

exp.start()

print("\n=== EXPERIMENT RUNNING ===\n")

try:
    while True:
        if not exp.is_running():
            break

        ddp.update(pro.depth_filtered_m, depth_setpoint)

        if ddp.closed:
            print("\n[DISPLAY CLOSED] Aborting experiment\n")
            exp.abort()
            break

        line = ser.read_line()
        if not line:
            continue

        if not exp.is_valid_csv(line):
            continue

        tel.update(line)

        if isinstance(con, (SquareWaveController)):
            current_setpoint = con.get_command()
            pro.process(tel, current_setpoint, None)
        elif isinstance(con, ManualController):
            current_setpoint = con.get_command()
            depth_setpoint = con.depth_target
            pro.process(tel, current_setpoint, depth_setpoint)
        else:
            depth_setpoint   = depth_wave.get_command()
            current_setpoint = con.get_command(pro.depth_filtered_m or 0.0, depth_setpoint)
            pro.process(tel, current_setpoint, depth_setpoint)

        ddp.update(pro.depth_filtered_m, depth_setpoint)

        log.write_raw(tel)
        log.write_processed(pro)

        try:
            cmd = inn.get_command(pro.actuator_mm, pro.actuator_setpoint_mm)
            ser.write_command(cmd)
        except Exception as e:
            print(f"[CONTROLLER ERROR] {e}")

        if tel.battery_v is not None and tel.battery_v <= BATTERY_CUTOFF_V:
            print("\n[SAFETY STOP] Battery below threshold\n")
            exp.abort()
            break

except KeyboardInterrupt:
    print("\n[CTRL+C] Aborting experiment\n")
    exp.abort()

finally:
    print("\nShutting down...\n")

    try:
        ser.write_command("S")
    except:
        pass

    ddp.close()
    log.close_raw()
    ser.close()

    print(f"Saved experiment in: {exp.get_folder_path()}")

    import os
    if os.path.exists(f"{exp.get_folder_path()}/processed.csv"):
        vis = Plotter(exp.get_folder_path())
        vis.plot()
