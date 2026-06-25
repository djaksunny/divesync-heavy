# RX format:
# time_ms, actuator_raw, motor_cmd, depth_m, pressure_mbar, temp_c, depth_ok, battery_v
# e.g. 15361,1098,0,0.1290,1025.61,23.78,1,4.24

# TX format:
# motor_cmd, return_telemetry, stop_actuator


import os
import time
from datetime import datetime
import serial
import serial.tools.list_ports


# =========================
# CONFIG
# =========================

EXPERIMENT_DURATION_S = 10

FOLDER_PATH = f"data/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
os.makedirs(FOLDER_PATH, exist_ok=True)

print(f"\nExperiment directory: {FOLDER_PATH}\n")


# =========================
# SERIAL PORT SELECTION
# =========================

port_list = []

print("Available COM ports:\n")

for index, port in enumerate(serial.tools.list_ports.comports()):
    port_list.append(port)
    print(f"[{index}]: {port.name} ({port.description})")

print("")


while True:
    try:
        com_index = int(input("Select a COM port (index): ").strip())

        COM_PORT = port_list[com_index].name
        print(f"\nSelected COM port: {COM_PORT}\n")

        break

    except ValueError:
        print("Error: please enter a valid number\n")

    except IndexError:
        print(f"Error: enter a number between 0 and {len(port_list) - 1}\n")


ser = serial.Serial(COM_PORT, 115200, timeout=1)
print(f"Connected to {COM_PORT}\n")


# =========================
# FILE SETUP
# =========================

boot_path = f"{FOLDER_PATH}/boot.txt"
raw_path = f"{FOLDER_PATH}/raw.csv"

boot_file = open(boot_path, "w")
raw_file = open(raw_path, "w")


# =========================
# STATE VARIABLES
# =========================

depth_sensor_ok = False
actuator_ready = False
logging_started = False

start_time_s = None


# =========================
# MAIN LOOP
# =========================

try:
    print("Waiting for device...\n")

    while True:
        raw = ser.readline()
        if not raw:
            continue

        line = raw.decode("utf-8", errors="ignore").strip()

        # -------------------------
        # Boot logging (pre-start)
        # -------------------------
        if not logging_started:
            boot_file.write(line + "\n")

        # -------------------------
        # State detection
        # -------------------------
        if "DEPTH_SENSOR_OK" in line:
            depth_sensor_ok = True
            print("Depth sensor ready")

        if "LOW_LEVEL_DEPTH_ACTUATOR_INTERFACE_READY" in line:
            actuator_ready = True
            print("Actuator interface ready")

        # -------------------------
        # Start condition
        # -------------------------
        if depth_sensor_ok and actuator_ready and not logging_started:
            logging_started = True
            start_time_s = time.time()

            print("\nSYSTEM READY → STARTING LOGGING\n")

            raw_file.write(
                "time_ms,actuator_raw,motor_cmd,depth_m,pressure_mbar,temp_c,depth_ok,battery_v\n"
            )

            boot_file.write("=== READY SIGNAL RECEIVED ===\n")

        # -------------------------
        # Logging phase
        # -------------------------
        if logging_started and line.count(',') == 7:
            raw_file.write(line + "\n")

            elapsed_s = time.time() - start_time_s

            if elapsed_s >= EXPERIMENT_DURATION_S:
                print("\nExperiment complete → stopping logging\n")
                break


finally:
    boot_file.close()
    raw_file.close()
    ser.close()
    