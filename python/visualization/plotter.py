import pandas as pd
import matplotlib.pyplot as plt

class Plotter:
    def __init__(self, folder_path):
        self._folder_path = folder_path
        self._df = pd.read_csv(f"{self._folder_path}/processed.csv")
        self._df.dropna(how='all', inplace=True)

    # format: time_s, depth_filtered_m, depth_setpoint_m, actuator_mm, actuator_setpoint_mm, motor_cmd
    def plot(self):
        fig, axes = plt.subplots(3, 1, sharex=True)

        fig.suptitle(f"Experiment {self._folder_path[5:]} Results", fontsize=14, fontweight="bold")

        time = self._df["time_s"]

        # Depth plot (plot 1)
        depth = self._df["depth_filtered_m"]
        axes[0].plot(time, depth, label="Depth (m)", color="blue")
        if self._df["depth_setpoint_m"].notna().any():
            depth_setpoint = self._df["depth_setpoint_m"]
            axes[0].plot(time, depth_setpoint, label="Depth Setpoint (m)", color="green")
        axes[0].legend()
        axes[0].grid(True)

        # Actuator plot (plot 2)
        actuator = self._df["actuator_mm"]
        axes[1].plot(time, actuator, label="Actuator Position (mm)", color="red")
        if self._df["actuator_setpoint_mm"].notna().any():
            actuator_setpoint = self._df["actuator_setpoint_mm"]
            axes[1].plot(time, actuator_setpoint, label="Actuator Setpoint (mm)", color="purple")
        axes[1].legend()
        axes[1].grid(True)

        # PWM plot (plot 3)
        pwm = self._df["motor_cmd"]
        axes[2].plot(time, pwm, label="PWM", color="orange")
        axes[2].legend()
        axes[2].grid(True)

        axes[2].set_xlabel("Time (s)")

        plt.show()

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Map target path to relative directory
    data_dir = Path("data")

    if not data_dir.exists() or not data_dir.is_dir():
        print("Error: The 'data' directory does not exist.\n")
        sys.exit(1)

    print("=== DIVESYNC HEAVY - DATA PLOTTING AND REPLAY INTERFACE ===\n")

    print("Available experiments:\n")

    # Gather available folders
    folder_list = sorted([str(f) for f in data_dir.iterdir() if f.is_dir()])

    # Display available choices in terminal
    for idx, folder in enumerate(folder_list):
        print(f"[{idx}] {Path(folder).name}")
    print()

    selected_folder_path = None

    while True:
        try:
            if len(folder_list) == 0:
                print("No folders available. Exiting plotter.\n")
                selected_folder_path = None
                sys.exit(0)
                
            folder_index = int(input("Select a folder (index): ").strip())
            selected_folder_path = folder_list[folder_index]
            print(f"\nSelected folder path: {selected_folder_path}. Plotting...\n")
            break
            
        except ValueError:
            print("Error: please enter a valid number\n")
        except IndexError:
            if len(folder_list) == 1:
                print(f"Error: enter 0")
            else:
                print(f"Error: enter a number between 0 and {len(folder_list) - 1}\n")

    # Replay execution
    try:
        plotter = Plotter(folder_path=selected_folder_path)
        plotter.plot()
    except FileNotFoundError:
        print(f"Error: 'processed.csv' not found inside {selected_folder_path}\n")
