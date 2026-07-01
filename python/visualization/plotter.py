import pandas as pd
import matplotlib.pyplot as plt

class Plotter:
    def __init__(self, path):
        self._df = pd.read_csv(path)
        self._df.dropna(how='all', inplace=True)

    # format: time_s, depth_filtered_m, depth_setpoint_m, actuator_mm, actuator_setpoint_mm, motor_cmd
    def plot(self):
        fig, axes = plt.subplots(3, 1, sharex=True)

        time = self._df["time_s"]

        # Depth plot (plot 1)
        depth = self._df["depth_filtered_m"]
        axes[0].plot(time, depth, label="Depth (m)", color="blue")
        if self._df["depth_setpoint_m"].notna().any():
            depth_setpoint = self._df["depth_setpoint_m"]
            axes[0].plot(time, depth_setpoint, label="Depth Setpoint (m)", color="green")
        axes[0].legend()

        # Actuator plot (plot 2)
        actuator = self._df["actuator_mm"]
        axes[1].plot(time, actuator, label="Actuator Position (mm)", color="red")
        if self._df["actuator_setpoint_mm"].notna().any():
            actuator_setpoint = self._df["actuator_setpoint_mm"]
            axes[1].plot(time, actuator_setpoint, label="Actuator Setpoint (mm)", color="purple")
        axes[1].legend()

        # PWM plot (plot 3)
        pwm = self._df["motor_cmd"]
        axes[2].plot(time, pwm, label="PWM", color="orange")
        axes[2].legend()

        plt.show()
