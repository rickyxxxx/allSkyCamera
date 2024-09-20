import io
import os
import sys
import json
import time
import datetime
import traceback
import zipfile
from typing import Iterable, Optional
from threading import Thread, Event

from flask import Flask, render_template, send_file, jsonify, request


IMAGE_PER_PAGE = 12
FILTERED_LIST = []

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


@app.route('/select')
def select():
    return render_template('select.html')


def make_filters(cond: str) -> str:
    if cond == 'All':
        return "True"
    cond = cond.replace(" ", "")
    cond_list = cond.split(";")
    l = []
    for c in cond_list:
        if 'g' in cond:
            c = c.replace('g', 'gain')
        if 'o' in cond:
            c = c.replace('o', 'offset')
        if 'e' in cond:
            if "ms" in c:
                c = c.replace("ms", "*1000")
            elif "us" in c:
                c = c.replace("us", "*1")
            elif "s" in c:
                c = c.replace("s", "*1000000")
            c = c.replace('e', 'exposure')

        l.append(c)

    return " and ".join(l)


@app.route('/clear_filter')
def clear_filter():
    global FILTERED_LIST
    FILTERED_LIST = []
    return jsonify({'message': 'Filter cleared successfully'})


@app.route('/apply_filter/<string:tag>/<string:cond>')
def apply_filter(tag: str, cond: str):
    global tags, image_specs, FILTERED_LIST
    if tag.lower() != "all":
        names = tags.get(tag)
    else:
        names = [f.rstrip('.png') for f in os.listdir(f"{PROJECT_PATH}/shared/img") if f.endswith('.png')]

    def unpack_specs(f: str) -> Iterable:
        fields = "timestamp", "exposure", "gain", "offset"
        return [
            image_specs.get(f, {}).get(field, "unknown")
            for field in fields
        ]

    FILTERED_LIST = []

    img_w_specs = [
        (f"{f}.png", *unpack_specs(f"{f}.png"))
        for f in names
    ]

    try:
        for img_name, timestamp, exposure, gain, offset in img_w_specs:
            print(make_filters(cond))
            if eval(make_filters(cond)):
                FILTERED_LIST.append((img_name, timestamp, exposure, gain, offset))
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Invalid filter condition"})

    if not FILTERED_LIST:
        return jsonify({"message": "No image matched all the conditions. Returning all images"})

    return jsonify({"message": "Filter applied successfully"})


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

    if FILTERED_LIST:
        img_w_specs = FILTERED_LIST

    page_start = page * IMAGE_PER_PAGE
    page_end = page_start + IMAGE_PER_PAGE

    print(f"page_start: {page_start}, page_end: {page_end}")
    print(f"img_w_specs: {img_w_specs}")
    print(len(img_w_specs))
    return jsonify(img_w_specs[page_start: page_end])


@app.route('/download_all_images/<string:ext>')
def download_images(ext: str):
    memory_file = io.BytesIO()
    ext = ext.split(";")
    with zipfile.ZipFile(memory_file, 'w') as zf:
        if FILTERED_LIST:
            for img_name, *_ in FILTERED_LIST:
                for e in ext:
                    iname = f"{img_name.rstrip('.png')}.{e}"
                    zf.write(os.path.join(f"{PROJECT_PATH}/shared/img", iname), iname)
        else:
            for filename in os.listdir(f"{PROJECT_PATH}/shared/img"):
                e = filename.split(".")[-1]
                if e not in ext:
                    continue
                zf.write(os.path.join(f"{PROJECT_PATH}/shared/img", filename), filename)
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name='images.zip')


@app.route('/delete_all_images/<string:ext>')
def delete_images(ext: str):
    ext = ext.split(";")

    image_files = [
        f for f in os.listdir(f"{PROJECT_PATH}/shared/img")
        for e in ext if f.endswith(f".{e}")
    ]

    if FILTERED_LIST:
        image_files = [
            f"{f}.{e}"
            for f, *_ in FILTERED_LIST
            for e in ext
        ]

    for filename in image_files:
        os.remove(os.path.join(f"{PROJECT_PATH}", "shared", "img", filename))
    return jsonify({'message': 'All images deleted'})


@app.route('/get_total_pages')
def get_total_pages():
    image_count = len([f for f in os.listdir(f"{PROJECT_PATH}/shared/img") if f.endswith('.png')])
    if FILTERED_LIST:
        image_count = len(FILTERED_LIST)
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
    print()
    if scheduler is not None:
        terminate_scheduler.set()
        print("Waiting for scheduler to stop")
        scheduler.join()
        print("Scheduler stopped")
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


@app.route('/get_image_list/<string:cond>')
def get_image_list(cond):
    if cond == 'all':
        files = []
        for file in os.listdir(f"{PROJECT_PATH}/shared/img"):
            if file.endswith('.png'):
                files.append(file.rstrip('.png'))
        return jsonify({"img_list": files})
    else:
        pass


@app.route('/get_preview_images')
def get_preview_images():
    image_list = sorted(os.listdir(f"{PROJECT_PATH}/shared/img"))
    image_list.reverse()
    if len(image_list) == 1:
        return jsonify({"img_name": "NONE"})
    while not image_list[0].endswith('.png'):
        if len(image_list) == 1:
            return jsonify({"img_name": "NONE"})
        image_list.pop(0)

    return jsonify({"img_name": image_list[0]})


@app.route('/add_tag/<string:tag_name>')
def add_tag(tag_name: str):
    global current_tag
    current_tag = tag_name
    return jsonify({'message': f'Tag {tag_name} added'})


@app.route('/stop_tagging')
def stop_tagging():
    global current_tag
    current_tag = None
    return jsonify({'message': 'Tagging stopped'})


@app.route('/get_tags')
def get_tags():
    global tags
    data = {'tags': list(tags.keys())}
    print(data)
    return jsonify(data)


def get_time_stamp():
    current_time = datetime.datetime.now()
    if debug:
        return current_time.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3]
    return current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]


def start_scheduler_thread(count: int):
    global scheduler, terminate_scheduler, cam, settings, image_specs, scheduler_running
    if scheduler_running:
        return
    scheduler_running = True
    terminate_scheduler.clear()  # reset the terminate flag

    def event_loop():
        global scheduler_running, running_eta, current_tag, tags
        interval = settings['interval']
        exposure = settings['exposure']
        gain = settings['gain']
        offset = settings['offset']
        loop_start_time = time.time()
        start_time = time.time()
        info = {"exposure": f"{exposure/1e6:.1f}", "gain": gain, "offset": offset, "timestamp": get_time_stamp()}
        for i in range(count):
            while time.time() - start_time < interval:
                if terminate_scheduler.is_set():
                    scheduler_running = False
                    return
                time.sleep(0.1)
            if terminate_scheduler.is_set():
                scheduler_running = False
                return
            start_time = time.time()
            array, _ = cam.expose(exposure, gain=gain, offset=offset)
            time_stamp = get_time_stamp()
            name = f"{PROJECT_PATH}/shared/img/{time_stamp}"
            if "\\" in name:
                name = name.replace("\\", "/")
            info["timestamp"] = time_stamp
            cam.array_to_fits(array, name, info)
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
            if current_tag:
                if not tags.get(current_tag):
                    tags[current_tag] = []
                tags[current_tag].append(time_stamp)
        terminate_scheduler.set()
        scheduler_running = False
        print("Scheduler finished")

    scheduler = Thread(target=event_loop)
    scheduler.start()


def reduce_tags():
    global tags
    files = set([f.rstrip(".png") for f in os.listdir(f"{PROJECT_PATH}/shared/img") if f.endswith('.png')])
    new_tags = {}
    for k, v in tags.items():
        l = []
        for img in v:
            if img in files:
                l.append(img)
        if len(l):
            new_tags[k] = l
    tags = new_tags


if __name__ == '__main__':
    debug = False
    cam: Optional[camera.Camera] = None
    scheduler_running = False
    running_eta = ""
    with open(f"{PROJECT_PATH}/shared/tags.json") as spec:
        tags = json.load(spec)
    reduce_tags()

    current_tag = None
    with open(f"{PROJECT_PATH}/shared/img/image_info.json") as spec:
        image_specs = json.load(spec)
    try:
        cam = camera.Camera(PROJECT_PATH, debug)
        settings = {'gain': 150, 'offset': 0, 'exposure': 100000, 'interval': 0}
        app.run(host='0.0.0.0', port=8080)
    finally:
        with open(f"{PROJECT_PATH}/shared/tags.json", 'w') as spec:
            json.dump(tags, spec)
        if scheduler is not None:
            terminate_scheduler.set()
            scheduler.join()
        cam.close()
        print("Server closed")
