import tkinter as tk


class DepthDisplay:
    def __init__(self):
        self.closed = False

        self.root = tk.Tk()
        self.root.title("DiveSync Heavy Depth Control")

        self.depth_label = tk.Label(
            self.root,
            text="Depth: --- m",
            font=("Arial", 24)
        )
        self.depth_label.pack(padx=20, pady=10)

        self.setpoint_label = tk.Label(
            self.root,
            text="Setpoint: --- m",
            font=("Arial", 24)
        )
        self.setpoint_label.pack(padx=20, pady=10)

        self.error_label = tk.Label(
            self.root,
            text="Error: --- m",
            font=("Arial", 24)
        )
        self.error_label.pack(padx=20, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self._close)

        # draw window once
        self.root.update()

    def _close(self):
        self.closed = True
        self.root.destroy()

    def update(self, depth, setpoint):
        if self.closed:
            return

        # process pending tkinter events
        self.root.update()

        if depth is not None:
            self.depth_label.config(
                text=f"Depth: {depth:.3f} m"
            )

        if setpoint is not None:
            self.setpoint_label.config(
                text=f"Setpoint: {setpoint:.3f} m"
            )

        if depth is not None and setpoint is not None:
            error = setpoint - depth
            self.error_label.config(
                text=f"Error: {error:.3f} m"
            )
        else:
            self.error_label.config(text="Error: --- m")

        self.root.update_idletasks()

    def close(self):
        if not self.closed:
            self.closed = True
            self.root.destroy()
