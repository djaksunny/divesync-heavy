import pygame
import serial
import time

# ----------------------------
# CONFIG
# ----------------------------
PORT = "COM7"
BAUD = 115200

PWM_MAX = 255
DEADZONE = 0.1

# ----------------------------
# SERIAL
# ----------------------------
ser = serial.Serial(PORT, BAUD, timeout=0.01)
time.sleep(2)

# ----------------------------
# PYGAME INIT
# ----------------------------
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise RuntimeError("No joystick detected")

joy = pygame.joystick.Joystick(0)
joy.init()

print("Joystick ready:", joy.get_name())

# ----------------------------
# STATE
# ----------------------------
pwm = 0
depth = 0.0

def apply_deadzone(v):
    return 0.0 if abs(v) < DEADZONE else v

# ----------------------------
# LOOP
# ----------------------------
while True:
    pygame.event.pump()

    # ----------------------------
    # READ JOYSTICK → PWM
    # ----------------------------
    axis = joy.get_axis(1)
    axis = apply_deadzone(axis)

    pwm = int(-axis * PWM_MAX)
    pwm = max(-PWM_MAX, min(PWM_MAX, pwm))

    ser.write(f"U:{-pwm}\n".encode("utf-8"))

    # ----------------------------
    # READ SERIAL (non-blocking)
    # ----------------------------
    try:
        line = ser.readline().decode("utf-8", errors="ignore").strip()

        if line and line.count(",") >= 4:
            parts = line.split(",")

            # assumes depth is 4th field
            depth = float(parts[3])

    except:
        pass

    # ----------------------------
    # DISPLAY IN TERMINAL
    # ----------------------------
    print(f"\rPWM: {pwm:4d} | Depth: {depth:.3f} m", end="")

    time.sleep(0.02)
