import time
import pygame
import serial

# 1404 is neutral buoyancy with most tether inside water

ser = serial.Serial("COM7", 115200, timeout=1)

pygame.init()
pygame.joystick.init()

joystick = pygame.joystick.Joystick(0)
joystick.init()

while True:
    pygame.event.pump()
    pwm = 255 * joystick.get_axis(1)
    ser.write(f"U:{pwm}\n".encode("utf-8"))
    time.sleep(0.05)
