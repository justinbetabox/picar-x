from flask import Flask, Response, request, render_template
import cv2
from threading import Thread
from robot_hat.utils import reset_mcu
import os
import sys
from time import sleep, time, strftime, localtime
import numpy as np
from vilib import Vilib
from picarx import Picarx

reset_mcu()
sleep(0.2)            

app = Flask(__name__)
video_stream_widget = Vilib()
px = Picarx()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/video_feed")
def video_feed():
    return Response(video_stream_widget.show_frame(), mimetype='multipart/x-mixed-replace;boundary=frame')
    
@app.route("/ProcessCommands", methods=["POST"])
def ProcessCommands():
    if request.args.get('command') == 'forward': #type: ignore
        px.forward()
    elif request.args.get('command') == 'backward': #type: ignore
        px.backward()
    elif request.args.get('command') == 'left': #type: ignore
        px.set_dir_servo_angle(-30)
    elif request.args.get('command') == 'right': #type: ignore
        px.set_dir_servo_angle(30)
    elif request.args.get('command') == 'stop': #type: ignore
        px.stop()
    elif request.args.get('command') == 'straight': #type: ignore
        px.set_dir_servo_angle(0)
    elif request.args.get('command') == 'camup': #type: ignore
        px.set_camera_servo2_angle(-10)
    elif request.args.get('command') == 'camdown': #type: ignore
        px.set_camera_servo2_angle(10)
    elif request.args.get('command') == 'camleft': #type: ignore
        px.set_camera_servo1_angle(10)
    elif request.args.get('command') == 'camright': #type: ignore
        px.set_camera_servo1_angle(-10)
    elif request.args.get('command') == 'color_detect': #type: ignore
        if video_stream_widget.color_detect == False:
            video_stream_widget.color_detect = True
        else:
            video_stream_widget.color_detect = False
    elif request.args.get('command') == 'human_face_detect': #type: ignore
        if video_stream_widget.human_face_detect == False:
            video_stream_widget.human_face_detect = True
        else:
            video_stream_widget.human_face_detect = False
    elif request.args.get('command') == 'speedup': #type: ignore
        if px.speed <= 90:
            px.speed += 10
    elif request.args.get('command') == 'speeddown': #type: ignore
        if px.speed > 10:
            px.speed -= 10
    elif request.args.get('command') == 'exit': #type: ignore
        video_stream_widget.endCapture()
        os.execv(sys.executable, ['python'] + [sys.argv[0]])
    return('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
