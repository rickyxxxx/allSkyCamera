import io
import os
import sys
import json
import time
import datetime
import zipfile
from typing import Iterable, Optional
from threading import Thread, Event

from flask import Flask, render_template, send_file, jsonify, request


# check and initialize the project path
try:
    PROJECT_PATH = os.environ["ALL_SKY_CAMERA"]
    print(f"Project path loaded: {PROJECT_PATH}")
    sys.path.append(f"{PROJECT_PATH}/web/python")
    import camera
except KeyError:
    raise RuntimeError("Please set the environment variable ALL_SKY_CAMERA to the project path !!!")

# configure the Flask server
app = Flask(__name__, static_folder=f"{PROJECT_PATH}/shared", template_folder=f"{PROJECT_PATH}/web/html")
scheduler: Optional[Thread] = None
terminate_scheduler = Event()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/images')
def images():
    with open(f"{PROJECT_PATH}/shared/img/image_info.json") as spec:
        img_specs = json.load(spec)

    def unpack_specs(f: str) -> Iterable:
        fields = "timestamp", "exposure", "gain", "offset"
        return [img_specs[f][field] for field in fields]

    def is_image(f: str) -> bool:
        suffixes = '.jpg', '.png', '.jpeg'
        return any(f.endswith(suffix) for suffix in suffixes)

    img_w_specs = [
        (f, *unpack_specs(f))
        for f in os.listdir(f"{PROJECT_PATH}/shared/img")
        if is_image(f)
    ]

    return jsonify(img_w_specs)


@app.route('/download_images')
def download_images():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in os.listdir(f"{PROJECT_PATH}/shared/img"):
            if not filename.endswith('.fits'):
                continue
            zf.write(os.path.join(f"{PROJECT_PATH}/shared/img", filename), filename)
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name='images.zip')


@app.route('/start_scheduler', methods=['POST'])
def start_scheduler():
    global settings
    data = request.json
    settings = {key: int(value) for key, value in data.items()}

    start_scheduler_thread()

    return jsonify({'message': 'Scheduler started successfully'})


@app.route('/stop_scheduler')
def stop_scheduler():
    global scheduler, terminate_scheduler, scheduler_running
    if scheduler is not None:
        terminate_scheduler.set()
        scheduler.join()
        scheduler = None
    scheduler_running = False
    return jsonify({'message': 'Scheduler stopped successfully'})


@app.route('/get_scheduler_status')
def get_scheduler_status():
    global scheduler_running
    return jsonify({'running': scheduler_running})


@app.route('/get_settings')
def get_settings():
    global settings
    return jsonify(settings)


def get_time_stamp():
    current_time = datetime.datetime.now()
    return current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]


def start_scheduler_thread():
    global scheduler, terminate_scheduler, cam, settings, image_specs, scheduler_running
    terminate_scheduler.clear()     # reset the terminate flag

    def event_loop():
        interval = settings['interval']
        exposure = settings['exposure']
        gain = settings['gain']
        offset = settings['offset']
        while not terminate_scheduler.is_set():
            for i in range(interval):
                if terminate_scheduler.is_set():
                    return
                time.sleep(1)
            print(f"Camera Exposing with exposure:{exposure}  gain:{gain}  offset:{offset}")
            array, _ = cam.expose(exposure, gain=gain, offset=offset)
            time_stamp = get_time_stamp()
            name = f"{PROJECT_PATH}/shared/img/{time_stamp}"
            cam.array_to_fits(array, f"{name}.fits")
            cam.array_to_png(array, f"{name}.png")
            image_specs[f"{name}.png"] = {
                "timestamp": time_stamp, "exposure": exposure, "gain": gain, "offset": offset
            }
            with open(f"{PROJECT_PATH}/shared/img/image_info.json", 'w') as spec:
                json.dump(image_specs, spec)

    scheduler = Thread(target=event_loop)
    scheduler.start()
    scheduler_running = True


if __name__ == '__main__':
    cam: Optional[camera.Camera] = None
    scheduler_running = False
    try:
        image_specs = {}
        cam = camera.Camera(PROJECT_PATH)
        settings = {'gain': 10, 'offset': 140, 'exposure': 10000, 'interval': 2}
        app.run(host='0.0.0.0', port=8080)
    finally:
        if scheduler is not None:
            terminate_scheduler.set()
            scheduler.join()
        cam.close()
        print("Server closed")
