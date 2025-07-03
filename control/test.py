#!/usr/bin/env python3
from flask import Flask, request, jsonify, Response
import time
import cv2
from picarx import Picarx   # Assumes Picarx is available as provided
from vilib import Vilib     # Handles video feed and detection

app = Flask(__name__)

# Initialize and start camera
car = Picarx()
Vilib.camera_start(vflip=False, hflip=False, size=(640, 480))

# Defaults
DEFAULT_SPEED      = 50
STEERING_ANGLE     = 30
CAMERA_PAN_STEP    = 5
CAMERA_TILT_STEP   = 5
AVAILABLE_COLORS   = ["red", "orange", "yellow", "green", "blue", "purple", "magenta"]

# State
current_speed    = DEFAULT_SPEED
current_steering = 0
current_pan      = 0
current_tilt     = 0
face_enabled     = False
color_enabled    = False
selected_color   = AVAILABLE_COLORS[0]

def steering_label(angle: int) -> str:
    if angle < 0:
        return "Left"
    elif angle > 0:
        return "Right"
    else:
        return "Straight"

@app.route('/')
def index():
    options = "".join(f'<option value="{c}">{c.title()}</option>' for c in AVAILABLE_COLORS)
    return f"""<!DOCTYPE html>
<html>
<head>
  <title>Robot Car Controller</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin:0; padding:0; }}
    #topbar {{ background:#f0f0f0; padding:10px; display:flex; justify-content:center; gap:30px; align-items:center; }}
    .toggle {{ position:relative; display:inline-block; width:50px; height:24px; }}
    .toggle input {{ opacity:0; width:0; height:0; }}
    .slider {{ position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0; background:#ccc; transition:.4s; border-radius:24px; }}
    .slider:before {{ position:absolute; content:""; height:20px; width:20px; left:2px; bottom:2px; background:white; transition:.4s; border-radius:50%; }}
    .toggle input:checked + .slider {{ background:#2196F3; }}
    .toggle input:checked + .slider:before {{ transform:translateX(26px); }}
    .toggle-label {{ margin-left:8px; font-size:.9em; }}
    #colorSelect {{ font-size:.9em; padding:2px; }}
    #videoFeed {{ display:block; margin:20px auto; border:2px solid #333; }}
    #status {{ margin:10px auto; text-align:center; font-size:1.1em; }}
    #instructions {{ margin:10px auto; text-align:center; }}
    span.value {{ font-weight:bold; }}
    button.popup {{ padding:4px 8px; }}
  </style>
</head>
<body>
  <div id="topbar">
    <span class="toggle-label">Human Face Detection</span>
    <label class="toggle">
      <input type="checkbox" id="faceToggle">
      <span class="slider"></span>
    </label>
    <span class="toggle-label">Color Detection</span>
    <select id="colorSelect">
      {options}
    </select>
    <label class="toggle">
      <input type="checkbox" id="colorToggle">
      <span class="slider"></span>
    </label>
    <button id="popupBtn" class="popup">Calibrate</button>
  </div>
  <img id="videoFeed" src="/video_feed" width="640" height="480" alt="Video Feed"/>
  <div id="status">
    Speed: <span id="speedValue" class="value">{DEFAULT_SPEED}</span>
     | Steering: <span id="steeringValue" class="value">{steering_label(current_steering)}</span>
     | Pan: <span id="panValue" class="value">{current_pan}</span>°
     | Tilt: <span id="tiltValue" class="value">{current_tilt}</span>°
  </div>
  <div id="instructions">
    <p>
      <strong>Drive:</strong> W/S: Forward/Backward, A/D: Left/Right<br>
      <strong>Camera:</strong> ←/→ Pan, ↑/↓ Tilt, Space: Reset Camera Position<br>
      <strong>Speed:</strong> O:-10, P:+10
    </p>
  </div>
  <script>
    let motorInt, steerInt, panInt, tiltInt;
    document.getElementById('faceToggle').addEventListener('change', function() {{
      sendCmd(this.checked ? 'enable_face' : 'disable_face');
    }});
    document.getElementById('colorToggle').addEventListener('change', function() {{
      sendCmd(this.checked ? 'enable_color' : 'disable_color');
    }});
    document.getElementById('colorSelect').addEventListener('change', function() {{
      sendCmd('set_color_' + this.value);
    }});
    document.getElementById('popupBtn').addEventListener('click', function() {{
      window.open('/popup', 'popup', 'width=400,height=200');
    }});
    document.addEventListener('keydown', e => {{
      const k = e.key, lk = k.toLowerCase();
      if (lk==='w'||lk==='s') {{
        if (!motorInt) motorInt = setInterval(()=>sendCmd(lk==='w'?'forward':'backward'),100);
      }} else if (lk==='a'||lk==='d') {{
        if (!steerInt) steerInt = setInterval(()=>sendCmd(lk==='a'?'left':'right'),100);
      }} else if (e.key==='ArrowLeft'||e.key==='ArrowRight') {{
        if (!panInt) panInt = setInterval(()=>sendCmd(e.key==='ArrowLeft'?'pan_left':'pan_right'),100);
      }} else if (e.key==='ArrowUp'||e.key==='ArrowDown') {{
        if (!tiltInt) tiltInt = setInterval(()=>sendCmd(e.key==='ArrowUp'?'tilt_up':'tilt_down'),100);
      }} else if (e.key===' ') {{
        sendCmd('reset_camera');
      }} else if (lk==='o'||lk==='p') {{
        sendCmd(lk==='o'?'speed_down':'speed_up');
      }}
    }});
    document.addEventListener('keyup', e => {{
      const k = e.key.toLowerCase();
      if (k==='w'||k==='s') {{ clearInterval(motorInt); motorInt=null; sendCmd('stop'); }}
      else if (k==='a'||k==='d') {{ clearInterval(steerInt); steerInt=null; sendCmd('reset_steering'); }}
      else if (e.key==='ArrowLeft'||e.key==='ArrowRight') {{ clearInterval(panInt); panInt=null; }}
      else if (e.key==='ArrowUp'||e.key==='ArrowDown') {{ clearInterval(tiltInt); tiltInt=null; }}
    }});
    function sendCmd(cmd) {{
      fetch('/keypress', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{key:cmd}})
      }})
      .then(r=>r.json())
      .then(data=>{{
        if (data.success) {{
          document.getElementById('speedValue').innerText    = data.speed;
          document.getElementById('steeringValue').innerText = data.steering;
          document.getElementById('panValue').innerText      = data.pan;
          document.getElementById('tiltValue').innerText     = data.tilt;
        }}
      }})
      .catch(console.error);
    }}
  </script>
</body>
</html>"""

@app.route('/popup')
def popup():
    return f"""<!DOCTYPE html>
<html>
<head>
  <title>Calibration</title>
  <style>
    body {{ font-family: Arial, sans-serif; text-align:center; padding:10px; }}
    label {{ display:block; margin:8px 0; }}
    input[type=range] {{ width:300px; }}
  </style>
</head>
<body>
  <label>
    Steering:
    <input id="steerSlider" type="range" min="-20" max="20" value="{current_steering}">
  </label>
  <label>
    Pan:
    <input id="panSlider" type="range" min="-20" max="20" value="{current_pan}">
  </label>
  <label>
    Tilt:
    <input id="tiltSlider" type="range" min="-20" max="20" value="{current_tilt}">
  </label>
  <script>
    document.getElementById('steerSlider').oninput = e => {{
      fetch('/calibrate_steering', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{value:parseInt(e.target.value)}})
      }});
    }};
    document.getElementById('panSlider').oninput = e => {{
      fetch('/calibrate_pan', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{value:parseInt(e.target.value)}})
      }});
    }};
    document.getElementById('tiltSlider').oninput = e => {{
      fetch('/calibrate_tilt', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{value:parseInt(e.target.value)}})
      }});
    }};
  </script>
</body>
</html>"""

@app.route('/calibrate_steering', methods=['POST'])
def calibrate_steering():
    global current_steering
    val = int(request.get_json(force=True)['value'])
    try:
        car.dir_servo_calibrate(val)
        current_steering = val
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/calibrate_pan', methods=['POST'])
def calibrate_pan():
    global current_pan
    val = int(request.get_json(force=True)['value'])
    try:
        car.cam_pan_servo_calibrate(val)
        current_pan = val
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/calibrate_tilt', methods=['POST'])
def calibrate_tilt():
    global current_tilt
    val = int(request.get_json(force=True)['value'])
    try:
        car.cam_tilt_servo_calibrate(val)
        current_tilt = val
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/keypress', methods=['POST'])
def keypress():
    global current_speed, current_steering, current_pan, current_tilt
    global face_enabled, color_enabled, selected_color

    data = request.get_json(force=True)
    key = data.get('key','').lower()
    if not key:
        return jsonify(success=False, error='No key provided'), 400

    try:
        # Driving & steering
        if key == 'forward':
            car.forward(current_speed)
        elif key == 'backward':
            car.backward(current_speed)
        elif key == 'left':
            current_steering = -STEERING_ANGLE
            car.set_dir_servo_angle(current_steering)
        elif key == 'right':
            current_steering = STEERING_ANGLE
            car.set_dir_servo_angle(current_steering)
        elif key == 'stop':
            car.stop()
        elif key == 'reset_steering':
            current_steering = 0
            car.set_dir_servo_angle(0)
        # Speed
        elif key == 'speed_down':
            current_speed = max(0, current_speed - 10)
        elif key == 'speed_up':
            current_speed = min(100, current_speed + 10)
        # Camera pan/tilt/reset
        elif key == 'pan_left':
            current_pan = max(current_pan - CAMERA_PAN_STEP, car.CAM_PAN_MIN)
            car.set_cam_pan_angle(current_pan)
        elif key == 'pan_right':
            current_pan = min(current_pan + CAMERA_PAN_STEP, car.CAM_PAN_MAX)
            car.set_cam_pan_angle(current_pan)
        elif key == 'tilt_up':
            current_tilt = min(current_tilt + CAMERA_TILT_STEP, car.CAM_TILT_MAX)
            car.set_cam_tilt_angle(current_tilt)
        elif key == 'tilt_down':
            current_tilt = max(current_tilt - CAMERA_TILT_STEP, car.CAM_TILT_MIN)
            car.set_cam_tilt_angle(current_tilt)
        elif key == 'reset_camera':
            current_pan = 0
            current_tilt = 0
            car.set_cam_pan_angle(0)
            car.set_cam_tilt_angle(0)
        # Face detection toggle
        elif key == 'enable_face':
            face_enabled = True
            Vilib.face_detect_switch(True)
        elif key == 'disable_face':
            face_enabled = False
            Vilib.face_detect_switch(False)
        # Color detection toggle
        elif key == 'enable_color':
            color_enabled = True
            Vilib.color_detect(selected_color)
        elif key == 'disable_color':
            color_enabled = False
            Vilib.close_color_detection()
        # Color selection
        elif key.startswith('set_color_'):
            col = key.split('set_color_')[1]
            if col in AVAILABLE_COLORS:
                selected_color = col
                if color_enabled:
                    Vilib.color_detect(col)
            else:
                return jsonify(success=False, error='Unknown color'), 400
        else:
            return jsonify(success=False, error='Invalid command'), 400

        return jsonify(
            success=True,
            command=key,
            speed=current_speed,
            steering=steering_label(current_steering),
            pan=current_pan,
            tilt=current_tilt
        )
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

def generate_frames():
    """Continuously yield JPEG frames from Vilib.img."""
    while True:
        frame = Vilib.img
        if frame is None:
            continue
        ret, buf = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(0.05)

@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

if __name__ == '__main__':
    car.reset()
    print("Starting Robot Car Controller with full calibration popup…")
    app.run(host='0.0.0.0', port=5000, debug=False)