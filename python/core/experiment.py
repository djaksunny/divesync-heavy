# Handle all experiment setup prior to run and basic data verification

import os
import time
from datetime import datetime
import json
from enum import Enum
import serial.tools.list_ports

class Experiment:

    class States(Enum):
        NOT_STARTED = 0
        HANDSHAKE = 1
        READY = 2
        RUNNING = 3
        STOPPED = 4

    def __init__(self):
        print("=== DIVESYNC HEAVY - DATA COLLECTION INTERFACE ===")

        # Experiment identity + folder
        self._experiment_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        self._folder_path = f"data/{self._experiment_id}"
        os.makedirs(self._folder_path, exist_ok=True)

        print(f"\nExperiment directory: {self._folder_path}\n")

        # State
        self._state = self.States.HANDSHAKE

        # Config
        self._experiment_duration_s = None
        self._start_time_s = None

        # Handshake flags (internal only)
        self._depth_sensor_ok = False
        self._actuator_ready = False

        # Boot logging
        self._boot_path = f"{self._folder_path}/boot.txt"
        self._boot_file = open(self._boot_path, "w")

        # Metadata
        self._config = {
            "experiment-id": self._experiment_id,
            "control-mode": None,
            "requested-duration": None,
            "actual-duration": None,
            "start-time": None,
            "start-time-readable": None,
            "notes": None
        }

    def setup_experiment(self):
        control_methods = ["manual", "pid", "rl"]

        while True:
            user_input = input("Control mode [manual / pid / rl] or index [0 / 1 / 2]: ").strip().lower()            
            if user_input in control_methods:
                self.mode = user_input
                self._config["control-mode"] = self.mode
                break              
            try:
                index = int(user_input)
                if 0 <= index < len(control_methods):
                    self.mode = control_methods[index]
                    self._config["control-mode"] = self.mode
                    break
            except ValueError:
                pass
                
            print("Invalid mode. Try again.")

        while True:
            try:
                duration = float(input("Experiment duration (seconds): ").strip())
                self._experiment_duration_s = duration
                self._config["requested-duration"] = duration
                break
            except ValueError:
                print("Enter a numeric value.")

        notes = input("Notes (optional): ").strip()
        if notes:
            self._config["notes"] = notes

        print("\nConfiguration complete\n")
        for k, v in self._config.items():
            print(f"{k}: {v}")
        print("")

        # Serial port selection
        self.com_port = None
        port_list = []
        print("Available COM ports:\n")

        for index, port in enumerate(serial.tools.list_ports.comports()):
            port_list.append(port)
            print(f"[{index}]: {port.name} ({port.description})")

        print("")

        while True:
            try:
                if len(port_list) == 0:
                    print("No ports available. Terminating experiment.\n")
                    self._terminate()
                    self.com_port = None
                    return
                com_index = int(input("Select a COM port (index): ").strip())
                self.com_port = port_list[com_index].device
                print(f"\nSelected COM port: {self.com_port}\n")
                break
            except ValueError:
                print("Error: please enter a valid number\n")
            except IndexError:
                if len(port_list) == 1:
                    print(f"Error: enter 0")
                else:
                    print(f"Error: enter a number between 0 and {len(port_list) - 1}\n")

    def handshake_protocol(self, raw):
        line = raw.strip()

        # Always log boot phase
        if self._state == self.States.HANDSHAKE:
            self._boot_file.write(line + "\n")
            self._boot_file.flush()

        # Detect hardware readiness
        if "DEPTH_SENSOR_OK" in line:
            self._depth_sensor_ok = True
            print("Depth sensor ready")

        if "LOW_LEVEL_DEPTH_ACTUATOR_INTERFACE_READY" in line:
            self._actuator_ready = True
            print("Actuator ready")

        # Transition to READY
        if (
            self._depth_sensor_ok and
            self._actuator_ready and
            self._state == self.States.HANDSHAKE
        ):
            self._state = self.States.READY

            self._boot_file.close()

            print("\nSYSTEM READY\n")

    def is_ready(self):
        return self._state == self.States.READY

    def get_folder_path(self):
        return self._folder_path

    def start(self):
        if self._state == self.States.READY:
            print("Starting experiment...")
            self._start_time_s = time.time()
            self._config["start-time"] = self._start_time_s
            self._config["start-time-readable"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._state = self.States.RUNNING

    def _terminate(self):
        with open(f"{self._folder_path}/metadata.json", "w") as f:
            json.dump(self._config, f, indent=4)

    def abort(self):
        if self._state == self.States.RUNNING:
                print("Aborting experiment...")
                self._state = self.States.STOPPED
                elapsed_s = time.time() - self._start_time_s
                self._config["actual-duration"] = elapsed_s
                self._terminate()
                print("Experiment aborted\n")
                print(f"EXPERIMENT DIRECTORY {self._folder_path}\n")

    def is_valid_csv(self, line):
        if self._state == self.States.RUNNING and line.count(",") == 7:
            return line
        return None

    def is_running(self):
        if self._state != self.States.RUNNING:
            return False

        elapsed = time.time() - self._start_time_s

        if elapsed >= self._experiment_duration_s:
            self._state = self.States.STOPPED
            self._config["actual-duration"] = elapsed
            self._terminate()
            print("\nExperiment complete -> stopping logging\n")
            return False

        return True
