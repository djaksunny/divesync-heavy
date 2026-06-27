# Logs to raw.csv data during experiments

class Logger:
    def __init__(self, folder_path):
        self._raw_path = f"{folder_path}/raw.csv"
        self._raw_file = open(self._raw_path, "w")
        self._raw_file.write("time_ms,actuator_raw,motor_cmd,depth_m,pressure_mbar,temp_c,depth_ok,battery_v\n")

    def write_raw(self, line):
        # Assumes line is validated
        self._raw_file.write(f"{line}\n")
        self._raw_file.flush()

    def close_raw(self):
        self._raw_file.close()
