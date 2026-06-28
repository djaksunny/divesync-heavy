# Reads serial, handles TX/RX to BCD

import serial

class SerialManager:
    def __init__(self, port_name):
        if port_name is None:
            raise RuntimeError("SerialManager: No COM port provided")

        self._ser = serial.Serial(port_name, 115200, timeout=1)

        print(f"Connected to {port_name}\n")

        # only write after port is confirmed open
        self._ser.write("RST\n".encode("utf-8"))

    def read_line(self):
        # RX from serial
        return self._ser.readline().decode("utf-8").strip()

    def write_command(self, command_string):
        # TX over serial
        self._ser.write(f"{command_string.strip()}\n".encode("utf-8"))

    def close(self):
        self._ser.close()
