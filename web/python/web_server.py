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


IMAGE_PER_PAGE = 12

# check and initialize the project path
try:
    print(os.environ)
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


@app.route('/gallery')
def gallery():
    return render_template('gallery.html')


@app.route('/images/<int:page>')
def images(page: int):
    global image_specs

    def unpack_specs(f: str) -> Iterable:
        fields = "timestamp", "exposure", "gain", "offset"
        return [
            image_specs.get(f, {}).get(field, "unknown")
            for field in fields
        ]

    def is_image(f: str) -> bool:
        suffixes = '.jpg', '.png', '.jpeg'
        return any(f.endswith(suffix) for suffix in suffixes)

    img_w_specs = [
        (f, *unpack_specs(f))
        for f in os.listdir(f"{PROJECT_PATH}/shared/img")
        if is_image(f)
    ]

    page_start = page * IMAGE_PER_PAGE
    page_end = page_start + IMAGE_PER_PAGE

    print(f"page_start: {page_start}, page_end: {page_end}")
    print(f"img_w_specs: {img_w_specs}")
    print(len(img_w_specs))
    return jsonify(img_w_specs[page_start: page_end])


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


@app.route('/get_total_pages')
def get_total_pages():
    image_count = len([f for f in os.listdir(f"{PROJECT_PATH}/shared/img") if f.endswith('.png')])
    pages = (image_count + IMAGE_PER_PAGE - 1) // IMAGE_PER_PAGE
    return jsonify({"totalPages": pages})


@app.route('/start_scheduler/<int:count>', methods=['POST'])
def start_scheduler(count: int):
    global settings
    data = request.json
    settings = {key: int(value) for key, value in data.items()}

    start_scheduler_thread(count)

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
    return jsonify({'running': "r" if scheduler_running else "i"})


@app.route('/get_progress')
def get_progress():
    global running_eta
    return jsonify({'eta': running_eta})


@app.route('/get_settings')
def get_settings():
    global settings
    return jsonify(settings)


@app.route('/get_preview_images')
def get_preview_images():
    pass


def get_time_stamp():
    current_time = datetime.datetime.now()
    return current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]


def start_scheduler_thread(count: int):
    global scheduler, terminate_scheduler, cam, settings, image_specs, scheduler_running
    if scheduler_running:
        return
    scheduler_running = True
    terminate_scheduler.clear()  # reset the terminate flag

    def event_loop():
        global scheduler_running, running_eta
        interval = settings['interval']
        exposure = settings['exposure']
        gain = settings['gain']
        offset = settings['offset']
        loop_start_time = time.time()
        start_time = time.time()
        for i in range(count):
            while time.time() - start_time < interval:
                if terminate_scheduler.is_set():
                    return
                time.sleep(0.1)
            start_time = time.time()
            print(f"Camera Exposing with exposure:{exposure}  gain:{gain}  offset:{offset}")
            array, _ = cam.expose(exposure, gain=gain, offset=offset)
            time_stamp = get_time_stamp()
            name = f"{PROJECT_PATH}/shared/img/{time_stamp}"
            cam.array_to_fits(array, name)
            cam.array_to_png(array, name)
            image_specs[f"{time_stamp}.png"] = {
                "timestamp": time_stamp, "exposure": exposure, "gain": gain, "offset": offset
            }
            with open(f"{PROJECT_PATH}/shared/img/image_info.json", 'w') as spec:
                json.dump(image_specs, spec)
            eta = (time.time() - loop_start_time) / (i + 1) * (count - i - 1)
            time_elapsed = time.time() - loop_start_time
            running_eta = (f"{i+1}/{count}\t\t"
                           f"{int(time_elapsed // 60)}m {int(time_elapsed % 60)}s/{int(eta // 60)}m {int(eta % 60)}s")
        terminate_scheduler.set()
        scheduler_running = False
        print("Scheduler finished")

    scheduler = Thread(target=event_loop)
    scheduler.start()


if __name__ == '__main__':
    cam: Optional[camera.Camera] = None
    scheduler_running = False
    running_eta = ""
    with open(f"{PROJECT_PATH}/shared/img/image_info.json") as spec:
        image_specs = json.load(spec)
    try:
        cam = camera.Camera(PROJECT_PATH, True)
        settings = {'gain': 150, 'offset': 0, 'exposure': 100000, 'interval': 0}
        app.run(host='0.0.0.0', port=8080)
    finally:
        if scheduler is not None:
            terminate_scheduler.set()
            scheduler.join()
        cam.close()
        print("Server closed")
