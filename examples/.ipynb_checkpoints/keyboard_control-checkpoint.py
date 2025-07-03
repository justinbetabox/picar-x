#!/usr/bin/env python3
from picarx import Picarx
from time import sleep
import readchar

manual = '''
Press keys on keyboard to control PiCar-X!
    w: Forward
    a: Turn left
    s: Backward
    d: Turn right
    i: Head up
    k: Head down
    j: Turn head left
    l: Turn head right
    ctrl+c: Exit the program
'''

def show_info():
    # ANSI clear screen + move cursor home
    print("\033[2J\033[H", end='')
    print(manual)

def main():
    pan_angle = 0
    tilt_angle = 0

    show_info()
    # __enter__ will init; __exit__ will stop & cleanup GPIO
    with Picarx() as px:
        try:
            while True:
                key = readchar.readkey().lower()

                if key in ('w','a','s','d','i','k','j','l'):
                    # Drive controls
                    if   key == 'w':
                        px.set_dir_servo_angle(0);    px.forward(80)
                    elif key == 's':
                        px.set_dir_servo_angle(0);    px.backward(80)
                    elif key == 'a':
                        px.set_dir_servo_angle(-30);  px.forward(80)
                    elif key == 'd':
                        px.set_dir_servo_angle(30);   px.forward(80)

                    # Head controls
                    elif key == 'i':
                        tilt_angle = min(tilt_angle + 5,  30)
                    elif key == 'k':
                        tilt_angle = max(tilt_angle - 5, -30)
                    elif key == 'l':
                        pan_angle  = min(pan_angle  + 5,  30)
                    elif key == 'j':
                        pan_angle  = max(pan_angle  - 5, -30)

                    # Apply head movement
                    px.set_cam_tilt_angle(tilt_angle)
                    px.set_cam_pan_angle( pan_angle )
                    sleep(0.5)

                    # Stop driving after each command
                    px.forward(0)
                    show_info()

                # Exit on Ctrl+C
                elif key == readchar.key.CTRL_C:
                    break

        except KeyboardInterrupt:
            # clean exit on second Ctrl+C
            pass

    # context-manager __exit__ has called px.stop() and GPIO.cleanup()

if __name__ == "__main__":
    main()