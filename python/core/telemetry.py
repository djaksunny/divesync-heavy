# takes raw line from serial and parses it for easy access to telemetry data without repetitive parsing
# format: time_ms, actuator_raw, motor_cmd, depth_m, pressure_mbar, temp_c, depth_ok, battery_v

class Telemetry:
    def __init__(self, line):
        self.update(line) # reuse update logic

    def update(self, line):
        # Splits CSV line
        self._parsed = line.strip().split(",")

        # Modify variables
        self.time_ms = int(self._parsed[0])
        self.actuator_raw = int(self._parsed[1])
        self.motor_cmd = int(self._parsed[2])
        self.depth_m = float(self._parsed[3])
        self.pressure_mbar = float(self._parsed[4])
        self.temp_c = float(self._parsed[5])
        self.depth_ok = int(self._parsed[6])
        self.battery_v = float(self._parsed[7])
