import numpy as np
from flask import Flask, render_template, Response, request
import cv2
import time
import threading
from camera import Camera
app = Flask(__name__, template_folder='.')

# Global variable to store the numpy array
image_array = np.random.randint(0, 256, (480, 640), dtype=np.uint8)


def generate_frames_from_array():
    global image_array
    while True:
        ret, buffer = cv2.imencode('.jpg', image_array)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames_from_array(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/update_image', methods=['POST'])
def update_image():
    global image_array
    data = request.json
    new_image = np.array(data['image'], dtype=np.uint8)
    image_array = new_image
    return "Image updated"


@app.route('/control', methods=['POST'])
def control():
    # Handle control actions here
    return "Control action received"


def update_image_loop():
    global image_array
    while True:
        image_array, _ = cam.expose(10_000)
        # # Update the image_array with new data
        # image_array = np.random.randint(0, 256, (480, 640), dtype=np.uint8)
        # time.sleep(0.1)  # Update every second


if __name__ == '__main__':
    import os

    PROJECT_PATH = os.environ["ALL_SKY_CAMERA"]
    cam = Camera(PROJECT_PATH)

    threading.Thread(target=update_image_loop, daemon=True).start()
    app.run(debug=True, host='192.168.0.73')