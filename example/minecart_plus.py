from picarx import Picarx
from time import sleep

px = Picarx()
last_state = ""
current_state = ""
px_power = 10
offset = 20


def outHandle():
    global last_state, current_state
    if last_state == 'left':
        px.set_dir_servo_angle(30)
        px.backward(10)
    elif last_state == 'right':
        px.set_dir_servo_angle(-30)
        px.backward(10)
    while True:
        gm_state = px.get_line_status()
        print("outHandle %s"%(gm_state))
        currentSta = gm_state
        if currentSta != last_state:
            break
    sleep(0.001)


if __name__=='__main__':
    try:
        while True:
            gm_state = px.get_line_status()
            if gm_state != "out":
                last_state = gm_state
            if gm_state == 'forward':
                px.set_dir_servo_angle(0)
                px.forward(px_power) 
            elif gm_state == 'right':
                px.set_dir_servo_angle(offset)
                px.forward(px_power) 
            elif gm_state == 'left':
                px.set_dir_servo_angle(-offset)
                px.forward(px_power) 
            elif gm_state == 'out':
                outHandle()
    except KeyboardInterrupt:
        px.stop()
        print('quit')
    except Exception as e:
        px.stop()
        print(e)
    finally:
        px.stop()


                