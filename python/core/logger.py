# Logs to raw.csv data during experiments

class Logger:
    def __init__(self, folder_path):
        # Setup raw file
        self._raw_path = f"{folder_path}/raw.csv"
        self._raw_file = open(self._raw_path, "w")
        self._raw_file.write("time_ms,actuator_raw,motor_cmd,depth_m,pressure_mbar,temp_c,depth_ok,battery_v\n")

        # Setup processed file
        self._processed_path = f"{folder_path}/processed.csv"
        self._processed_file = open(self._processed_path, "w")
        self._processed_file.write("time_s,actuator_mm,actuator_setpoint_mm,depth_filtered_m,depth_setpoint_m,motor_cmd\n")

        # Setup state file
        self._state_path = f"{folder_path}/state.csv"
        self._state_file = open(self._state_path, "w")
        self._state_file.write("time_s,depth_m,depth_setpoint_m,depth_error_m,velocity_mps\n")

    # Raw file write functions
    def write_raw(self, tel):
        # Assumes line is validated
        self._raw_file.write(f"{tel.raw_csv}\n")
        self._raw_file.flush()

    def close_raw(self):
        self._raw_file.close()

    # Processed file write functions
    def write_processed(self, pro):
        self._processed_file.write(f"{pro.processed_csv}\n")
        self._processed_file.flush()

    def close_processed(self):
        self._processed_file.close()

    def write_state(self, sta):
        self._state_file.write(f"{sta.state_csv}\n")
        self._state_file.flush()

    def close_state(self):
        self._state_file.close()
