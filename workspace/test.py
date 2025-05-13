#!/usr/bin/env python3
import sys
import termios
import tty
import signal
import time
from picarx import Picarx

POWER = 20

def getch() -> str:
    """
    Read a single character from stdin, with no Enter required.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def main():
    # Instantiate the car
    px = Picarx()
    # Start driving
    px.forward(POWER)
    print(f"Driving at {POWER}% power.  Press SPACE to stop.")

    # Disable Ctrl+C from killing the script so we can rely solely on SPACE
    signal.signal(signal.SIGINT, lambda *args: None)

    # Block until we see a space
    while True:
        c = getch()
        if c == ' ':
            print("\nSPACE detected; stopping motors.")
            px.stop()
            px.shutdown()
            break
        # Otherwise ignore all other keys

    print("Done.  Exiting.")

if __name__ == "__main__":
    main()