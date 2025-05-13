#!/usr/bin/env python3
import time
from picarx import Picarx

def main():
    px = Picarx()
    print("Reading raw grayscale values and status (0=white, 1=black)...")
    print("Press Ctrl+C to exit and reset servos/motors.")

    try:
        while True:
            # 1) grab the three ADC readings
            raw_vals = px.get_grayscale_data()
            # 2) convert them to black/white status
            status = px.get_line_status(raw_vals)
            # 3) print both
            if status[1] == 1:
                motion = "forward"
                px.forward(20)
            else:
                motion = "stop"
                px.stop()
            print(f"Raw ADC: {raw_vals}  |  Status: {motion}")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nInterrupted — cleaning up.")

    finally:
        px.reset()  # stop & center everything

if __name__ == "__main__":
    main()