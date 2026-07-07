import ctypes
import json
import sys
import pandas as pd
import matplotlib.pyplot as plt

# --- Palette (matches DepthDisplay) -------------------------------------
BG = "#0b0f14"          # window background
CARD_BG = "#121821"     # card / axes background
BORDER = "#1f2a37"      # card border / gridlines
FG_MUTED = "#5b6b7d"    # labels / captions
FG_PRIMARY = "#e6edf3"  # main readout values
ACCENT = "#3ba7ff"      # depth / primary accent
ACCENT_2 = "#8b5cf6"    # setpoint accent
OK = "#2ecc71"          # tertiary accent (PWM)
WARN = "#f5b942"
BAD = "#ff5d5d"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": CARD_BG,
    "axes.edgecolor": BORDER,
    "axes.labelcolor": FG_MUTED,
    "axes.titlecolor": FG_PRIMARY,
    "xtick.color": FG_MUTED,
    "ytick.color": FG_MUTED,
    "grid.color": BORDER,
    "text.color": FG_PRIMARY,
    "font.family": "Segoe UI",
    "legend.facecolor": CARD_BG,
    "legend.edgecolor": BORDER,
    "legend.labelcolor": FG_PRIMARY,
})


class Plotter:
    def __init__(self, folder_path):
        self._folder_path = folder_path
        self._df = pd.read_csv(f"{self._folder_path}/processed.csv")
        self._df.dropna(how='all', inplace=True)

    # format: time_s, depth_filtered_m, depth_setpoint_m, actuator_mm, actuator_setpoint_mm, motor_cmd
    def plot(self):
        fig, axes = plt.subplots(3, 1, sharex=True, figsize=(11, 8.5), dpi=100)
        fig.subplots_adjust(hspace=0.25)

        fig.suptitle(
            f"EXPERIMENT {self._folder_path[5:]} RESULTS", fontsize=14,
            fontweight="bold", color=FG_PRIMARY
        )

        time = self._df["time_s"]

        # Depth plot (plot 1)
        depth = self._df["depth_filtered_m"]
        axes[0].plot(time, depth, label="Depth (m)", color=ACCENT, linewidth=1.8)
        if self._df["depth_setpoint_m"].notna().any():
            depth_setpoint = self._df["depth_setpoint_m"]
            axes[0].plot(time, depth_setpoint, label="Depth Setpoint (m)", color=ACCENT_2, ls="--", linewidth=1.5)
        axes[0].legend(loc="upper right", framealpha=0.9)
        axes[0].grid(True, alpha=0.6)
        axes[0].set_title("DEPTH", loc="left", fontsize=11, fontweight="bold", color=FG_MUTED, pad=8)

        # Actuator plot (plot 2)
        actuator = self._df["actuator_mm"]
        axes[1].plot(time, actuator, label="Actuator Position (mm)", color=ACCENT, linewidth=1.8)
        if self._df["actuator_setpoint_mm"].notna().any():
            actuator_setpoint = self._df["actuator_setpoint_mm"]
            axes[1].plot(time, actuator_setpoint, label="Actuator Setpoint (mm)", color=ACCENT_2, ls="--", linewidth=1.5)
        axes[1].legend(loc="upper right", framealpha=0.9)
        axes[1].grid(True, alpha=0.6)
        axes[1].set_title("ACTUATOR", loc="left", fontsize=11, fontweight="bold", color=FG_MUTED, pad=8)

        # PWM plot (plot 3)
        pwm = self._df["motor_cmd"]
        axes[2].plot(time, pwm, label="PWM", color=OK, linewidth=1.8)
        axes[2].legend(loc="upper right", framealpha=0.9)
        axes[2].grid(True, alpha=0.6)
        axes[2].set_title("MOTOR CMD", loc="left", fontsize=11, fontweight="bold", color=FG_MUTED, pad=8)

        axes[2].set_xlabel("Time (s)", color=FG_MUTED, fontsize=11, fontweight="bold")

        for ax in axes:
            for spine in ax.spines.values():
                spine.set_color(BORDER)

        self._style_toolbar(fig)

        plt.show()

    @staticmethod
    def _enable_dark_titlebar(window):
        if sys.platform != "win32":
            return
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1)
            for attribute in (20, 19):  # 20 = Win10 20H1+, 19 = older builds
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
                if result == 0:
                    break
        except Exception:
            # not on Windows, or the DWM call isn't available — skip silently
            pass

    @staticmethod
    def _style_toolbar(fig):
        manager = getattr(fig.canvas, "manager", None)
        toolbar = getattr(manager, "toolbar", None)
        if toolbar is None:
            return
        try:
            toolbar.configure(background=CARD_BG)
            for child in toolbar.winfo_children():
                try:
                    child.configure(background=CARD_BG)
                except Exception:
                    pass
            window = getattr(manager, "window", None)
            if window is not None:
                window.configure(background=BG)
                Plotter._enable_dark_titlebar(window)
        except Exception:
            # backend isn't TkAgg or doesn't expose these widgets — skip styling
            pass

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

    def get_notes(folder):
        metadata_path = Path(folder) / "metadata.json"
        if not metadata_path.exists():
            return ""
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            return metadata.get("notes", "")
        except (json.JSONDecodeError, OSError):
            return ""

    # Display available choices in terminal
    for idx, folder in enumerate(folder_list):
        notes = get_notes(folder)
        if notes:
            print(f"[{idx}] {Path(folder).name} - {notes}")
        else:
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
