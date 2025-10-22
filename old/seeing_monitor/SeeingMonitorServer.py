from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import threading
import time
import os
import sys

import matplotlib
matplotlib.use('Agg')  # Ensures compatibility in headless mode

cam_path = os.path.join(os.path.dirname(__file__), '../camera')
sys.path.append(cam_path)
from camera import Camera

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state variables
state = {
    'exposure_time': 100.0,  # Default exposure time
    'gain': 1.0,           # Default gain
    'is_locked': False,
    'is_tracking': False
}

def generate_plot():
    """ Generates a dynamic plot and sends it to clients in real-time """
    while True:
        frame, exp_time = cam.expose(int(state['exposure_time']), gain=int(state['gain']), bbp=8, roi=((0, 0), (100, 100)))
        plt.figure()

        plt.imshow(frame.transpose(), cmap='gray')

        # Convert the plot to a PNG image
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode()

        plt.close()

        # Send the new image to the frontend
        socketio.emit('update_plot', {'image': img_base64})

        print("Updated plot")
        time.sleep(0.3)  # Update every 2 seconds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_state')
def get_state():
    """ Returns the current state of controls """
    return jsonify(state)

@socketio.on('change_setting')
def handle_change_setting(data):
    """ Handles the exposure time and gain setting change """
    state['exposure_time'] = float(data['exposure'])
    state['gain'] = float(data['gain'])
    socketio.emit('update_state', state)  # Broadcast updated state to all clients

@socketio.on('toggle_lock')
def handle_toggle_lock():
    """ Toggles the lock mode """
    state['is_locked'] = not state['is_locked']
    if not state['is_locked']:
        state['is_tracking'] = False  # Reset tracking if unlocked
    socketio.emit('update_state', state)

@socketio.on('toggle_track')
def handle_toggle_track():
    """ Toggles tracking mode (only when locked) """
    if state['is_locked']:
        state['is_tracking'] = not state['is_tracking']
    socketio.emit('update_state', state)


if __name__ == '__main__':
    import eventlet
    cam = Camera()
    cam.config_continuous_mode()

    eventlet.monkey_patch()
    threading.Thread(target=generate_plot, daemon=True).start()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

