# Reads serial, handles TX/RX to BCD

import serial

class SerialManager:
    def __init__(self, port_name):
        # Connect to serial
        self._ser = serial.Serial(port_name, 115200, timeout=1)
        print(f"Connected to {port_name}\n")
        self._ser.write("RST\n".encode("utf-8")) # restart BCD

    def read_line(self):
        # RX from serial
        return self._ser.readline()

    def write_command(self, command_string):
        # TX over serial
        self._ser.write(command_string.encode("utf-8"))
