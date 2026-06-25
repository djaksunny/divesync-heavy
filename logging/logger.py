import os
import json
import time
from datetime import datetime
import serial
import serial.tools.list_ports

print("=== DIVESYNC HEAVY - DATA COLLECTION INTERFACE ===")

# Experiment configuration
EXPERIMENT_ID = datetime.now().strftime('%Y%m%d-%H%M%S')
FOLDER_PATH = f"data/{EXPERIMENT_ID}"
os.makedirs(FOLDER_PATH, exist_ok=True)
print(f"\nExperiment directory: {FOLDER_PATH}\n")

# JSON setup
CONFIG = {"experiment-id": EXPERIMENT_ID,
          "control-mode": None,
          "requested-duration": None,
          "actual-duration": None,
          "start-time": None,
          "start-time-readable": None
          }

print("\n=== EXPERIMENT CONFIGURATION ===")

# Control mode
while True:
    mode = input("Control mode [manual / mpc / rl]: ").strip().lower()
    if mode in ["manual", "mpc", "rl"]:
        CONFIG["control-mode"] = mode
        break
    print("Invalid mode. Try again.")

# Duration
while True:
    try:
        duration = float(input("Experiment duration (seconds): ").strip())
        CONFIG["requested-duration"] = duration
        EXPERIMENT_DURATION_S = duration
        break
    except ValueError:
        print("Enter a numeric value.")

# Optional notes
notes = input("Notes (optional): ").strip()
CONFIG["notes"] = notes if notes else None

print("\nConfiguration complete\n")
for k, v in CONFIG.items():
    print(f"{k}: {v}")
print("")

# Serial port selection
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

# Connect and reset device (\n added to ensure microcontroller registers it)
ser = serial.Serial(COM_PORT, 115200, timeout=1)
print(f"Connected to {COM_PORT}\n")
ser.write("RST\n".encode("utf-8"))

# File setup
boot_path = f"{FOLDER_PATH}/boot.txt"
raw_path = f"{FOLDER_PATH}/raw.csv"

boot_file = open(boot_path, "w")
raw_file = open(raw_path, "w")

# State variables
depth_sensor_ok = False
actuator_ready = False
logging_started = False
start_time_s = None

# Main loop
try:
    print("Waiting for device...\n")

    while True:
        raw = ser.readline()
        if not raw:
            continue

        line = raw.decode("utf-8", errors="ignore").strip()

        # Log boot output until system is ready
        if not logging_started:
            boot_file.write(line + "\n")

        # Check hardware status flags
        if "DEPTH_SENSOR_OK" in line:
            depth_sensor_ok = True
            print("Depth sensor ready")

        if "LOW_LEVEL_DEPTH_ACTUATOR_INTERFACE_READY" in line:
            actuator_ready = True
            print("Low level system ready")

        # Initialize logging when both conditions are met
        if depth_sensor_ok and actuator_ready and not logging_started:
            logging_started = True
            start_time_s = time.time()
            CONFIG["start-time"] = start_time_s
            CONFIG["start-time-readable"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print("\nSYSTEM READY -> STARTING LOGGING (press Ctrl+C to abort)\n")
            raw_file.write(
                "time_ms,actuator_raw,motor_cmd,depth_m,pressure_mbar,temp_c,depth_ok,battery_v\n"
            )
            boot_file.write("=== READY SIGNAL RECEIVED ===\n")

        # Process and write valid CSV telemetry
        if logging_started and line.count(',') == 7:
            raw_file.write(line + "\n")
            raw_file.flush()  # Prevents data loss if script is aborted

            elapsed_s = time.time() - start_time_s
            if elapsed_s >= EXPERIMENT_DURATION_S:
                print("\nExperiment complete -> stopping logging\n")
                CONFIG["actual-duration"] = elapsed_s
                break

except KeyboardInterrupt:
    print("Aborting experiment...")
    elapsed_s = time.time() - start_time_s
    CONFIG["actual-duration"] = elapsed_s
    print("Experiment aborted")
    raw_file.write("=== EXPERIMENT ABORTED ===")

finally:
    # Write metadata to JSON
    with open(f"{FOLDER_PATH}/metadata.json", "w") as json_file:
        json.dump(CONFIG, json_file)

    boot_file.close()
    raw_file.close()
    ser.close()
