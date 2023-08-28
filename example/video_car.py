# #!/usr/bin/env python3

print('Please run under desktop environment (eg: vnc) to display the image window')

from robot_hat.utils import reset_mcu
from picarx import Picarx
from vilib import Vilib
from time import sleep

reset_mcu()
sleep(0.2)

px = Picarx()

def main():
    Vilib.camera_start(vflip=False,hflip=False)
    while True:
        Vilib.display(local=False,web=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("error:%s"%e)
    finally:
        px.stop()
        Vilib.camera_close()


        