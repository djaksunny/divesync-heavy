# Core
from core.experiment import Experiment
from core.serial_manager import SerialManager
from core.logger import Logger
from core.telemetry import Telemetry
from core.processor import Processor

# Controllers
from controllers.manual import ManualController
from controllers.pid import PIDController
# from controllers.rl import RLController
from controllers.waveform import SquareWaveController
from controllers.inner import InnerPIDController

# Visualization
from visualization.plotter import Plotter

# Config
BATTERY_CUTOFF_V  = 10.0
ACTUATOR_STROKE   = 50.0
DEPTH_WAVE_LOW    = 0.5
DEPTH_WAVE_HIGH   = 1.0
DEPTH_WAVE_PERIOD = 20.0

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

inn        = InnerPIDController((8, 2, 0), 130)
depth_wave = None

match exp.mode:
    case "manual":
        con = ManualController(ACTUATOR_STROKE)
    case "pid":
        con        = PIDController(ACTUATOR_STROKE, (1, 0.5, 0))
        depth_wave = SquareWaveController(DEPTH_WAVE_LOW, DEPTH_WAVE_HIGH, DEPTH_WAVE_PERIOD)
    # case "rl":
    #     con        = RLController(ACTUATOR_STROKE)
    #     depth_wave = SquareWaveController(DEPTH_WAVE_LOW, DEPTH_WAVE_HIGH, DEPTH_WAVE_PERIOD)
    case "sysid":
        con = SquareWaveController(5, 45, 20)
    case _:
        print("Invalid or unsupported controller mode")
        exit()

# Handshake
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

        line = ser.read_line()
        if not line:
            continue

        if not exp.is_valid_csv(line):
            continue

        tel.update(line)

        if depth_wave and pro.depth_filtered_m is not None:
            depth_setpoint   = depth_wave.get_command()
            current_setpoint = con.get_command(pro.depth_filtered_m, depth_setpoint)
            pro.process(tel, current_setpoint, depth_setpoint)
        else:
            current_setpoint = con.get_command()
            pro.process(tel, current_setpoint, None)

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

        if not exp.is_running():
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

    log.close_raw()
    ser.close()

    print(f"Saved experiment in: {exp.get_folder_path()}")

    vis = Plotter(exp.get_folder_path())
    vis.plot()
