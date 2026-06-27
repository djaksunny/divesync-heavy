import os
import json
import time
from datetime import datetime
import serial
import serial.tools.list_ports

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

# File setup

raw_path = f"{FOLDER_PATH}/raw.csv"

raw_file = open(raw_path, "w")

except KeyboardInterrupt:
    print("Aborting experiment...")
    elapsed_s = time.time() - start_time_s
    CONFIG["actual-duration"] = elapsed_s
    print("Experiment aborted")
    raw_file.write("=== EXPERIMENT ABORTED ===")

finally:
    # Write metadata to JSON


    boot_file.close()
    raw_file.close()
    ser.close()
