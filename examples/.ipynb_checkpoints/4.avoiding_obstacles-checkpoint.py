#!/usr/bin/env python3
from picarx import Picarx
import time

POWER          = 50
SafeDistance   = 40
DangerDistance = 20

def main():
    # __enter__ sets up, __exit__ calls _cleanup() for you
    with Picarx() as px:
        try:
            while True:
                dist = round(px.ultrasonic.read(), 2)
                print("distance:", dist)

                if   dist >= SafeDistance:
                    px.set_dir_servo_angle(0)
                    px.forward(POWER)
                elif dist >= DangerDistance:
                    px.set_dir_servo_angle(30)
                    px.forward(POWER)
                    time.sleep(0.1)
                else:
                    px.set_dir_servo_angle(-30)
                    px.backward(POWER)
                    time.sleep(0.5)

                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nInterrupted by user — exiting...")

if __name__ == "__main__":
    main()

