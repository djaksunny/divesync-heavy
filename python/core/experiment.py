# Handle all experiment setup prior to run and basic data verification

import os
import time
from datetime import datetime
import json
from enum import Enum


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
        self._com_port = None
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

        while True:
            mode = input("Control mode [manual / mpc / rl]: ").strip().lower()
            if mode in ["manual", "mpc", "rl"]:
                self._config["control-mode"] = mode
                break
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


    def handshake_protocol(self, raw):

        line = raw.decode("utf-8", errors="ignore").strip()

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

            self._start_time_s = time.time()

            self._config["start-time"] = self._start_time_s
            self._config["start-time-readable"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            self._boot_file.close()

            with open(f"{self._folder_path}/metadata.json", "w") as f:
                json.dump(self._config, f, indent=4)

            print("\nSYSTEM READY\n")


    def start(self):
        if self._state == self.States.READY:
            self._state = self.States.RUNNING


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

            print("\nExperiment complete -> stopping logging\n")
            return False

        return True
