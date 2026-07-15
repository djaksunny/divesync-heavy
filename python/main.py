# Core
from core.experiment import Experiment
from core.serial_manager import SerialManager
from core.logger import Logger
from core.merger import Merger
from core.telemetry import Telemetry
from core.processor import Processor
from core.state import State
from core.setpoint import SetpointGenerator

# Controllers
from controllers.manual import ManualController
from controllers.pid import PIDController
from controllers.rl import RLController
from controllers.inner import InnerPIDController

# Visualization
from visualization.plotter import Plotter
from visualization.display import DepthDisplay

# Config
BATTERY_CUTOFF_V      = 10.0
ACTUATOR_STROKE       = 100.0
ACTUATOR_EQUILIBRIUM  = 48.0
DEPTH_LOW             = 0.2
DEPTH_HIGH            = 0.7

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
sta = State()
ddp = DepthDisplay()
stp = SetpointGenerator(DEPTH_LOW, DEPTH_HIGH)

inn = InnerPIDController((8, 0, 0), 150)

match exp.mode:
    case "manual":
        con = ManualController(ACTUATOR_STROKE, ACTUATOR_EQUILIBRIUM)
    case "pid":
        con = PIDController(ACTUATOR_STROKE, ACTUATOR_EQUILIBRIUM, (2, 1, 5))
    case "rl":
        con = RLController(ACTUATOR_STROKE)
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

        # Phase 1: filter depth / convert actuator units (no controller output needed yet)
        pro.process_depth(tel)

        depth_setpoint = stp.get_setpoint()

        pro.depth_setpoint_m = depth_setpoint

        # Phase 2: update state now that depth + setpoint are both known
        sta.update(pro)

        # Phase 3: controller reads state, returns actuator setpoint
        current_setpoint = con.get_command(sta)

        # Phase 4: finalize processed record / csv
        pro.process_actuator(current_setpoint, depth_setpoint)

        ddp.update(pro.depth_filtered_m, depth_setpoint)

        log.write_raw(tel)
        log.write_processed(pro)
        log.write_state(sta)

        try:
            cmd = inn.get_command(pro.actuator_mm, pro.actuator_setpoint_mm)
            ser.write_command(cmd)
        except Exception as e:
            print(f"[CONTROLLER ERROR] {e}")

        # Safety: battery cutoff
        if (
            tel.battery_v is not None
            and tel.battery_v <= BATTERY_CUTOFF_V
        ):
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
    log.close_processed()
    log.close_state()
    ser.close()

    if hasattr(con, "finalize"):
        con.finalize(sta)

    print(f"Saved experiment in: {exp.get_folder_path()}")

    import os
    if os.path.exists(f"{exp.get_folder_path()}/processed.csv"):
        vis = Plotter(exp.get_folder_path())
        vis.plot()

    try:
        mer = Merger(exp.get_folder_path())
        mer.merge()
    except FileNotFoundError as e:
        print(f"[MERGE SKIPPED] {e}")
