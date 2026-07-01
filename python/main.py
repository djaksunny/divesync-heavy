# Core
from core.experiment import Experiment
from core.serial_manager import SerialManager
from core.logger import Logger
from core.telemetry import Telemetry
from core.processor import Processor
from core.waveform import SquareWaveGenerator

# Controllers
from controllers.manual import ManualController
from controllers.pid import PIDController
# from controllers.rl import RLController

# Visualization
from visualization.plotter import Plotter

# Config
BATTERY_CUTOFF_V = 10.0

# Setup
exp = Experiment()
exp.setup_experiment()

if exp.com_port is None:
    print("No COM port selected. Exiting.")
    exit()

ser = SerialManager(exp.com_port)
log = Logger(exp.get_folder_path())
tel = Telemetry()
sqw = SquareWaveGenerator(5, 45, 10)

# Select controller
match exp.mode:
    case "manual":
        con = ManualController()
        pro = Processor(False)
    case "pid":
        con = PIDController((10,7,0.05))
        pro = Processor(True)
    # case "rl":
    #     con = RLController()
        pro = Processor(True)
    case _:
        print("Invalid or unsupported controller mode")
        exit()

# Handshake
print("\n=== WAITING FOR DEVICE READY ===\n")

while not exp.is_ready():
    line = ser.read_line()
    exp.handshake_protocol(line)

# Start experiment
exp.start()

print("\n=== EXPERIMENT RUNNING ===\n")

# Main loop
try:
    while True:

        # Stop condition (central authority)
        if not exp.is_running():
            break

        # Read serial stream
        line = ser.read_line()
        if not line:
            continue

        # Validate telemetry format
        if not exp.is_valid_csv(line):
            continue

        # Parse telemetry
        tel.update(line)

        # Process telemetry
        pro.process(tel, sqw.value())

        # Log data
        log.write_raw(tel)
        log.write_processed(pro)

        # Controller output
        try:
            cmd = con.get_command(pro.actuator_mm, pro.actuator_setpoint_mm, pro.depth_filtered_m, pro.depth_setpoint_m)
            ser.write_command(cmd)
        except Exception as e:
            print(f"[CONTROLLER ERROR] {e}")

        # Safety: battery cutoff
        if tel.battery_v is not None and tel.battery_v <= BATTERY_CUTOFF_V:
            print("\n[SAFETY STOP] Battery below threshold\n")
            exp.abort()
            break

        # Safety: experiment timeout (handled internally too)
        if not exp.is_running():
            break

except KeyboardInterrupt:
    print("\n[CTRL+C] Aborting experiment\n")
    exp.abort()

finally:
    print("\nShutting down...\n")

    try:
        ser.write_command("S")  # stop actuator
    except:
        pass

    log.close_raw()
    ser.close()

    print(f"Saved experiment in: {exp.get_folder_path()}")

    vis = Plotter(exp.get_folder_path())
    vis.plot()
