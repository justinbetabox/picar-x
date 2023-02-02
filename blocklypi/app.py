from flask import Flask, Response, request, render_template
import cv2
from threading import Thread
from robot_hat.utils import reset_mcu
import sys
import time
import numpy as np
from vilib import Vilib
from picarx import Picarx
           
app = Flask(__name__)
px = Picarx()
video_stream_widget = Vilib()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/video_feed")
def video_feed():
    return Response(video_stream_widget.show_frame(), mimetype='multipart/x-mixed-replace;boundary=frame')

@app.route("/RunCode", methods=["POST"])
def RunCode():
    print(request.data)
    exec(request.data)
    return('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, threaded=True)
