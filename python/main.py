# Main orchestrator file

import time

# Core packages
from core.experiment import Experiment
from core.serial_manager import SerialManager
from core.logger import Logger
from core.telemetry import Telemetry

# Controller packages
from controllers.manual import ManualController
# from controllers.manual import PIDController
# from controllers.manual import RLController

# Visualizer packages
# from visualization.analysis import Analysis
# from visualization.live_plotter import LivePlotter

# Create experiment instance
exp = Experiment()
exp.setup_experiment()

# Ensure not empty
if exp.com_port is None:
    exit()

# Create serial manager instance
ser = SerialManager(exp.com_port)

# Create logger instance
log = Logger(exp._folder_path)

# Create telemetry instance
tel = Telemetry()

# Create controllers
match exp.mode:
    case "manual":
        con = ManualController()
    # case "pid":
    #     con = PIDController()
    # case "rl":
    #     con = RLController()

# Boot/handshake protocol
while not(exp.is_ready()):
    exp.handshake_protocol(ser.read_line())

# Begin experiment
exp.start()

# Timing setup
loop_hz = 20
dt = 1/ loop_hz
last = time.time()

while exp.is_running():
    if time.time() - last >= dt:
        last = time.time()
        try:
            line = ser.read_line()
            if exp.is_valid_csv(line):
                tel.update(line)
                log.write_raw(line)
                ser.write_command(con.get_command())
        except KeyboardInterrupt:
            exp.abort()
