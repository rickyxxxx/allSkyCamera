import io
import os
import sys
import time
import traceback
import zipfile
import psutil
import datetime
import platform
from typing import Iterable, Optional
from threading import Thread, Event

from astropy.io import fits
from flask import Flask, render_template, send_file, jsonify, request, Response
from zipstream import ZipStream
import zipstream


# check and initialize the project path
try:
    print(os.environ)
    PROJECT_PATH = os.environ["ALL_SKY_CAMERA"]
    print(f"Project path loaded: {PROJECT_PATH}")
    import_path = os.path.join(PROJECT_PATH, "web", "python")
    sys.path.append(import_path)
    import camera
except KeyError:
    raise RuntimeError("Please set the environment variable ALL_SKY_CAMERA to the project path !!!")

# configure the Flask server
static_folder = os.path.join(PROJECT_PATH, "shared")
template_folder = os.path.join(PROJECT_PATH, "web", "html")
app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)
scheduler: Optional[Thread] = None
terminate_scheduler = Event()
IMAGE_PER_PAGE = 8


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/gallery')
def gallery():
    internal_states['displaying_list'] = scan_images()
    return render_template('gallery.html')


def make_filters(cond: str) -> str:
    if cond.lower() == "all":
        return "True"
    time_mask = {"ms": "*1000", "us": "*1", "s": "*1000000"}
    field_mask = {"g": "gain", "o": "offset", "e": "exposure"}
    conditions = cond.replace(" ", "").split(";")

    condition_list = []
    for condition in conditions:
        for key, value in time_mask.items():
            if key not in condition:
                continue
            condition = condition.replace(key, value)
        for key, value in field_mask.items():
            if key not in condition:
                continue
            condition = condition.replace(key, value)
        condition_list.append(condition)

    conditions = " and ".join(condition_list)
    # filter out the images with unknown specs
    return "'unknown' not in tstamp and " + conditions


@app.route('/apply_filter/<string:tag>/<string:cond>')
def apply_filter(tag: str, cond: str):
    if tag.lower() == 'all' and cond.lower() == 'all':
        internal_states['displaying_list'] = scan_images()
        internal_states['condition'] = ""
        return jsonify({"message": "Filter removed"})

    existing_images = scan_images()

    if tag.lower() == "all":
        valid_images = existing_images
    else:
        valid_images = tags.get(tag, [])

    def spec_of(image: str) -> list:
        specs = image_specs.get(image, {})
        ts = specs.get("timestamp", "unknown")
        exp = int(specs.get("exposure", -1))
        g = int(specs.get("gain", -1))
        o = int(specs.get("offset", -1))
        return [ts, exp, g, o]

    filtered_images = []
    try:
        print("valid images:", valid_images)
        for i in valid_images:
            tstamp, exposure, gain, offset = spec_of(i)
            if eval(make_filters(cond)) and i in existing_images:
                filtered_images.append(i)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"message": "Invalid filter condition"})

    print(filtered_images)

    internal_states['displaying_list'] = filtered_images

    if len(filtered_images) == 0:
        internal_states['displaying_list'] = existing_images
        return jsonify({"message": "No images found !!! Displaying all images"})
    return jsonify({"message": f"Filter applied successfully {len(filtered_images)} images found"})


@app.route('/images/<int:page>')
def images(page: int):

    def unpack_specs(f: str) -> Iterable:
        fields = "timestamp", "exposure", "gain", "offset"
        return [
            image_specs.get(f, {}).get(field, "unknown")
            for field in fields
        ]

    img_w_specs = [
        (f, *unpack_specs(f))
        for f in internal_states['displaying_list']
    ]

    page_start = page * IMAGE_PER_PAGE
    page_end = page_start + IMAGE_PER_PAGE

    return jsonify(img_w_specs[page_start: page_end])


# @app.route('/download')
# def download_files():
#     filenames = internal_states['displaying_list']
#     existing_files = set(scan_images())  # make sure the files are still there
#     filenames = [f for f in filenames if f in existing_files]
#     filenames = [f"{f}.{e}" for f in filenames for e in ["fits", "png"]]
#
#     # Debug: Print filenames to ensure they are correct
#     print("Filenames to be downloaded:", filenames)
#
#     def generate():
#         for filename in filenames:
#             file_path = os.path.join(PROJECT_PATH, "shared", "img", filename)
#             # Debug: Check if the file exists
#             if not os.path.exists(file_path):
#                 print(f"File not found: {file_path}")
#                 continue
#             with open(file_path, 'rb') as f:
#                 while chunk := f.read(8192):
#                     yield chunk
#
#     return Response(generate(), content_type='application/octet-stream')

# @app.route('/download')
# def download_files():
#     filenames = internal_states['displaying_list']
#     existing_files = set(scan_images())  # make sure the files are still there
#     filenames = [f for f in filenames if f in existing_files]
#     filenames = [f"{f}.{e}" for f in filenames for e in ["fits", "png"]]
#
#     # Debug: Print filenames to ensure they are correct
#     print("Filenames to be downloaded:", filenames)
#
#     def generate():
#         for filename in filenames:
#             file_path = os.path.join(PROJECT_PATH, "shared", "img", filename)
#             # Debug: Check if the file exists
#             if not os.path.exists(file_path):
#                 print(f"File not found: {file_path}")
#                 continue
#             with open(file_path, 'rb') as f:
#                 file_data = f.read()
#                 name_bytes = filename.encode('utf-8')
#                 yield len(name_bytes).to_bytes(1, 'little')
#                 yield name_bytes
#                 yield len(file_data).to_bytes(4, 'little')
#                 yield file_data
#
#     return Response(generate(), content_type='application/octet-stream')
@app.route('/download')
def download_files():
    filenames = internal_states['displaying_list']
    existing_files = set(scan_images())  # make sure the files are still there
    filenames = [f for f in filenames if f in existing_files]
    filenames = [f"{f}.{e}" for f in filenames for e in ["fits", "png"]]

    # Debug: Print filenames to ensure they are correct
    # print("Filenames to be downloaded:", filenames)

    def generate():
        for filename in filenames:
            file_path = os.path.join(PROJECT_PATH, "shared", "img", filename)
            # Debug: Check if the file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue
            with open(file_path, 'rb') as f:
                file_data = f.read()
                name_bytes = filename.encode('utf-8')
                yield len(name_bytes).to_bytes(1, 'little')
                yield name_bytes
                yield len(file_data).to_bytes(4, 'little')
                yield file_data

    response = Response(generate(), content_type='application/octet-stream')
    response.headers['Content-Disposition'] = 'attachment; filename=image.bin'
    return response

# @app.route('/download')
# def download():
#     # List of file paths to include in the zip
#     filenames = internal_states['displaying_list']
#     existing_files = set(scan_images())  # make sure the files are still there
#     filenames = [f for f in filenames if f in existing_files]
#     filenames = [f"{f}.{e}" for f in filenames for e in ["fits", "png"]]
#
#     # Create a BytesIO object to hold the zip data
#     zip_buffer = io.BytesIO()
#
#     # Create a ZipFile object
#     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zs:
#         # Add files to the zip
#         for file in filenames:
#             file_path = os.path.join(PROJECT_PATH, "shared", "img", file)
#             # Debug: Print file path and check if the file exists
#             print(f"Adding file to zip: {file_path}")
#             if not os.path.exists(file_path):
#                 print(f"File not found: {file_path}")
#                 continue
#             with open(file_path, 'rb') as f:
#                 file_content = f.read()
#                 # Debug: Print file content length
#                 print(f"File content length: {len(file_content)}")
#                 zs.writestr(os.path.basename(file_path), file_content)
#
#     # Stream the zip file
#     zip_buffer.seek(0)
#     response = Response(zip_buffer, mimetype='application/zip')
#     response.headers['Content-Disposition'] = 'attachment; filename=images.zip'
#     return response

# @app.route('/download')
# def download():
#     # List of file paths to include in the zip
#     filenames = internal_states['displaying_list']
#     existing_files = set(scan_images())  # make sure the files are still there
#     filenames = [f for f in filenames if f in existing_files]
#     filenames = [f"{f}.{e}" for f in filenames for e in ["fits", "png"]]
#
#     # Create a ZipStream object
#     zs = ZipStream()
#
#     # Add files to the zip stream
#     for file in filenames:
#         file_path = os.path.join(PROJECT_PATH, "shared", "img", file)
#         # Debug: Print file path and check if the file exists
#         print(f"Adding file to zip: {file_path}")
#         if not os.path.exists(file_path):
#             print(f"File not found: {file_path}")
#             continue
#         with open(file_path, 'rb') as f:
#             file_content = f.read()
#             # Debug: Print file content length
#             print(f"File content length: {len(file_content)}")
#             zs.add(file_path, os.path.basename(file_path))
#
#     # Stream the zip file
#     response = Response(zs, mimetype='application/zip')
#     response.headers['Content-Disposition'] = 'attachment; filename=images.zip'
#     return response


# @app.route('/download_image/<string:ext>/<int:page>')
# def download_images(ext: str, page: int):
#     memory_file = io.BytesIO()
#     ext = ext.split(";")
#     pagesize = 50
#     with zipfile.ZipFile(memory_file, 'w') as zf:
#         page_start = page * pagesize
#         page_end = page_start + pagesize
#         package = internal_states['displaying_list'][page_start: page_end]
#         for img_timestamp in package:
#             for e in ext:
#                 it = f"{img_timestamp}.{e}"
#                 zf.write(os.path.join(f"{PROJECT_PATH}/shared/img", it), it)
#
#     memory_file.seek(0)
#     return send_file(memory_file, as_attachment=True, download_name=f'images_{page}.zip')


@app.route('/estimate_pagesize')
def estimate_pagesize():
    pagesize = 50
    image_count = len(internal_states['displaying_list'])
    pages = (image_count + pagesize - 1) // pagesize
    return jsonify({"totalPages": pages})


@app.route('/delete_all_images/')
def delete_images():
    global tags, image_specs
    ext = "fits;png".split(";")

    existing_list = set(scan_images())
    present_list = internal_states['displaying_list']
    intersect_list = [f for f in present_list if f in existing_list]

    image_files = [
        os.path.join(PROJECT_PATH, "shared", "img", f"{f}.{e}")
        for f in intersect_list
        for e in ext
    ]

    for filename in image_files:
        try:
            os.remove(filename)
        except FileNotFoundError:
            print(f"File not found: {filename}")

    internal_states['displaying_list'] = scan_images()
    for tag, img_timestamp in tags.items():
        for i in img_timestamp:
            if i not in internal_states['displaying_list']:
                img_timestamp.remove(i)
    # remove tags that has an empty list
    tags = {tag: img_timestamp for tag, img_timestamp in tags.items() if img_timestamp}

    image_specs = {
        img_timestamp: spec
        for img_timestamp, spec in image_specs.items()
        if img_timestamp in internal_states['displaying_list']
    }

    return jsonify({'message': f'{len(image_files) // 2} images deleted !!!'})


@app.route('/get_total_pages')
def get_total_pages():
    image_count = len(internal_states['displaying_list'])
    pages = (image_count + IMAGE_PER_PAGE - 1) // IMAGE_PER_PAGE
    return jsonify({"totalPages": pages})


@app.route('/start_scheduler/<int:count>', methods=['POST'])
def start_scheduler(count: int):
    data = request.json
    internal_states['settings'] = {key: int(value) for key, value in data.items()}

    create_task(count)

    return jsonify({'message': 'Scheduler started successfully'})


@app.route('/stop_scheduler')
def stop_scheduler():
    global scheduler
    if scheduler is not None:
        terminate_scheduler.set()
        scheduler.join()
        scheduler = None
    return jsonify({'message': 'Scheduler stopped successfully'})


@app.route('/get_scheduler_status')
def get_scheduler_status():
    return jsonify({'running': "r" if scheduler else "i"})


@app.route('/get_progress')
def get_progress():
    return jsonify({'eta': internal_states['eta']})


@app.route('/get_settings')
def get_settings():
    return jsonify(internal_states['settings'])


@app.route('/get_preview_images')
def get_preview_images():
    img_loc = os.path.join(PROJECT_PATH, "shared", "img")
    image_list = sorted(os.listdir(img_loc))
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
    global internal_states
    internal_states['current_tag'] = tag_name
    return jsonify({'message': f'Tag {tag_name} added'})


@app.route('/stop_tagging')
def stop_tagging():
    internal_states['current_tag'] = None
    return jsonify({'message': 'Tagging stopped'})


@app.route('/get_tags')
def get_tags():
    global tags
    existing_files = scan_images()
    filtered_tags = {}
    for tag_name, image_timestamp_list in tags.items():
        for image_timestamp in image_timestamp_list:
            if any(image_timestamp in f for f in existing_files):
                filtered_tags[tag_name] = image_timestamp_list
                break
    tags = filtered_tags
    data = {'tags': list(tags.keys())}
    return jsonify(data)


@app.route('/get_current_tag')
def get_current_tag():
    ctag = internal_states['current_tag'] or 'none'
    return jsonify({'tag': internal_states['current_tag']})


@app.route('/resources')
def resources():
    if os.name == 'nt' or platform.system() == 'Windows':
        disk_usage = psutil.disk_usage('C:')
    else:
        disk_usage = psutil.disk_usage('/')
    disk_info = f"Disk: {disk_usage.used // 1024**3} GB / {disk_usage.total // 1024**3} GB"
    estimated_pictures = int(disk_usage.free // (18.4 * 1024 ** 2))
    disk_info += f"\nFree: {disk_usage.free // 1024 ** 3}GB - (~{estimated_pictures} pictures)"
    memory = psutil.virtual_memory()
    memory_info = f"Memory: {memory.used // 1024**2} MB / {memory.total // 1024**2} MB"
    return jsonify({"disk": disk_info, "memory": memory_info})


def timestamp():
    cur_time_str = datetime.datetime.now()
    if os.name == 'nt' or platform.system() == 'Windows':
        # windows does not support ':' in file names
        return cur_time_str.strftime('%Y-%m-%dT%H-%M-%S.%f')[:-3]
    else:
        return cur_time_str.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]


def create_task(repeat: int) -> Response:
    global scheduler
    if scheduler is not None:
        return jsonify({'message': 'Scheduler already running'})
    terminate_scheduler.clear()

    try:    # get the settings from the internal states
        gain = int(internal_states['settings']['gain'])
        offset = int(internal_states['settings']['offset'])
        exposure = int(internal_states['settings']['exposure'])
        interval = int(internal_states['settings']['interval'])
    except ValueError:
        return jsonify({'message': 'Invalid settings'})
    except Exception:
        return jsonify({'message': 'Unknown error'})
    fits_header = {
        "exposure": f"{exposure / 1e6:.1f}",
        "gain": gain,
        "offset": offset,
        "timestamp": timestamp(),
        "tag": internal_states['current_tag'] or 'none'
    }

    def event_loop():
        total_time, timer = time.time(), time.time()
        for i in range(repeat):
            while time.time() - timer < interval:
                if terminate_scheduler.is_set():
                    return
                time.sleep(0.1)
            if terminate_scheduler.is_set():
                return
            timer = time.time()
            print("Exposing ...")
            array, _ = cam.expose(exposure, gain=gain, offset=offset)
            time_stamp = timestamp()
            filename = os.path.join(PROJECT_PATH, "shared", "img", time_stamp)
            fits_header["timestamp"] = time_stamp
            cam.array_to_fits(array, filename, fits_header)
            cam.array_to_png(array, filename)
            image_specs[time_stamp] = {
                "timestamp": time_stamp, "exposure": exposure, "gain": gain, "offset": offset
            }
            progress_str = f"{i+1}/{repeat}"
            time_elapsed = time.time() - total_time
            elapsed_str = f"{int(time_elapsed // 60)}m {int(time_elapsed % 60)}s"
            eta = (time.time() - total_time) / (i + 1) * (repeat - i - 1)
            eta_str = f"{int(eta // 60)}m {int(eta % 60)}s"
            internal_states['eta'] = f"{progress_str} - {elapsed_str}/{eta_str}"
            if curr_tag := internal_states['current_tag']:
                if tags.get(curr_tag):
                    tags[curr_tag].append(time_stamp)
                else:
                    tags[curr_tag] = [time_stamp]

    scheduler = Thread(target=event_loop)
    scheduler.start()
    scheduler.join()
    print("Scheduler finished")
    scheduler = None

# def start_scheduler_thread(count: int):
#     global scheduler, terminate_scheduler, cam, settings, image_specs, scheduler_running
#     if scheduler_running:
#         return
#     scheduler_running = True
#     terminate_scheduler.clear()  # reset the terminate flag
#
#     def event_loop():
#         global scheduler_running, running_eta, current_tag, tags
#         interval = settings['interval']
#         exposure = settings['exposure']
#         gain = settings['gain']
#         offset = settings['offset']
#         loop_start_time = time.time()
#         start_time = time.time()
#         info = {"exposure": f"{exposure/1e6:.1f}", "gain": gain, "offset": offset, "timestamp": timestamp()}
#         for i in range(count):
#             while time.time() - start_time < interval:
#                 if terminate_scheduler.is_set():
#                     scheduler_running = False
#                     return
#                 time.sleep(0.1)
#             if terminate_scheduler.is_set():
#                 scheduler_running = False
#                 return
#             start_time = time.time()
#             array, _ = cam.expose(exposure, gain=gain, offset=offset)
#             time_stamp = timestamp()
#             name = f"{PROJECT_PATH}/shared/img/{time_stamp}"
#             if "\\" in name:
#                 name = name.replace("\\", "/")
#             info["timestamp"] = time_stamp
#             cam.array_to_fits(array, name, info)
#             cam.array_to_png(array, name)
#             image_specs[f"{time_stamp}.png"] = {
#                 "timestamp": time_stamp, "exposure": exposure, "gain": gain, "offset": offset
#             }
#             with open(f"{PROJECT_PATH}/shared/img/image_info.json", 'w') as spec:
#                 json.dump(image_specs, spec)
#             eta = (time.time() - loop_start_time) / (i + 1) * (count - i - 1)
#             time_elapsed = time.time() - loop_start_time
#             running_eta = (f"{i+1}/{count}\t\t"
#                            f"{int(time_elapsed // 60)}m {int(time_elapsed % 60)}s/{int(eta // 60)}m {int(eta % 60)}s")
#             if current_tag:
#                 if not tags.get(current_tag):
#                     tags[current_tag] = []
#                 tags[current_tag].append(time_stamp)
#         terminate_scheduler.set()
#         scheduler_running = False
#         print("Scheduler finished")
#
#     scheduler = Thread(target=event_loop)
#     scheduler.start()


# def exist_csv(filename: str, header: list[str]) -> bool:
#     if os.path.exists(filename):
#         return True
#     with open(filename, 'w', newline='') as file:
#         writer = csv.writer(file)
#         writer.writerow(header)
#     return False
#
#
# def load_specs():
#     global tags, image_specs
#
#     image_loc = os.path.join(PROJECT_PATH, "shared", "img")
#     existing_images = set([
#         f.rstrip('.png')
#         for f in os.listdir(image_loc)
#         if f.endswith('.png')
#     ])
#
#     tag_header = ["tag name", "timestamp"]
#     tag_loc = os.path.join(PROJECT_PATH, "shared", "tags.csv")
#     tags = {}
#     if exist_csv(tag_loc, tag_header):
#         file = open(tag_loc, 'r')
#         csv_reader = csv.reader(file)
#         for i, row in enumerate(csv_reader):
#             if i == 0:
#                 continue
#             tag_name, time_str = row
#             if tags.get(tag_name):
#                 tags[tag_name].append(time_str)
#             else:
#                 tags[tag_name] = [time_str]
#         file.close()
#
#     img_header = ["timestamp", "exposure", "gain", "offset"]
#     img_spec_loc = os.path.join(PROJECT_PATH, "shared", "img", "image_info.csv")
#     image_specs = {}
#     if exist_csv(img_spec_loc, img_header):
#         file = open(img_spec_loc, 'r')
#         csv_reader = csv.reader(file)
#         img_info: dict[str, str] = {}
#         header = []
#         for i, row in enumerate(csv_reader):
#             if i == 0:
#                 header = row
#             else:
#                 for j, field in enumerate(header):
#                     img_info[field] = row[j]
#                 image_specs[img_info["timestamp"]] = img_info
#         file.close()
#
#
# def save_specs():
#     global tags, image_specs
#     tag_loc = os.path.join(PROJECT_PATH, "shared", "tags.csv")
#     with open(tag_loc, 'a', newline='') as file:
#         writer = csv.writer(file)
#         for tag, time_str in tags.items():
#             for ts in time_str:
#                 writer.writerow([tag, ts])
#
#     img_spec_loc = os.path.join(PROJECT_PATH, "shared", "img", "image_info.csv")
#     with open(img_spec_loc, 'a', newline='') as file:
#         writer = csv.writer(file)
#         for _, info in image_specs.items():
#             writer.writerow([info["timestamp"], info["exposure"], info["gain"], info["offset"]])
#
#     print("Specs saved")
#
#
# def overwrite_specs():
#     global tags, image_specs
#     tag_loc = os.path.join(PROJECT_PATH, "shared", "tags.csv")
#     with open(tag_loc, 'w', newline='') as file:
#         writer = csv.writer(file)
#         writer.writerow(["tag name", "timestamp"])
#         for tag, time_str in tags.items():
#             for ts in time_str:
#                 writer.writerow([tag, ts])
#
#     img_spec_loc = os.path.join(PROJECT_PATH, "shared", "img", "image_info.csv")
#     with open(img_spec_loc, 'w', newline='') as file:
#         writer = csv.writer(file)
#         writer.writerow(["timestamp", "exposure", "gain", "offset"])
#         for _, info in image_specs.items():
#             writer.writerow([info["timestamp"], info["exposure"], info["gain"], info["offset"]])
#
#     print("Specs saved")


def scan_images() -> list[str]:
    img_dir = os.path.join(PROJECT_PATH, "shared", "img")
    return [
        f.rstrip('.png')
        for f in os.listdir(img_dir)
        if f.endswith('.png')
    ]


def restore_png():
    img_dir = os.path.join(PROJECT_PATH, "shared", "img")
    fits_images = [f for f in os.listdir(img_dir) if f.endswith('.fits')]
    for fits in fits_images:
        png_path = os.path.join(img_dir, fits.replace('.fits', '.png'))
        if os.path.exists(png_path):
            continue
        camera.Camera.fits_to_png(os.path.join(img_dir, fits))
        print(f"Restored {fits} to {png_path}")


def read_fits_header(filename):
    with fits.open(filename) as hdul:
        header = hdul[0].header
        try:
            tag = header["TAG"]
        except KeyError:
            tag = 'none'
        except Exception:
            tag = 'none'
        try:
            res = {
                "exposure": header["EXPTIME"],
                "gain": header["EGAIN"],
                "offset": header["OFFSET"],
                "timestamp": header["DATE-OBS"],
                "tag": tag
            }

        except KeyError:
            res =  {
                "exposure": "unknown",
                "gain": "unknown",
                "offset": "unknown",
                "timestamp": "unknown",
                "tag": tag
            }
        return res


def load_specs():
    existing_files = scan_images()
    for img in existing_files:
        file_path = os.path.join(PROJECT_PATH, "shared", "img", f"{img}.fits")
        fits_header = read_fits_header(file_path)
        exp = int(float(fits_header["exposure"]) * 1e6)
        gain = int(fits_header["gain"])
        offset = int(fits_header["offset"])
        tstamp = fits_header["timestamp"]
        tag = fits_header['tag']
        image_specs[img] = {"timestamp": tstamp, "exposure": exp, "gain": gain, "offset": offset}
        if tag != "none":
            if tags.get(tag):
                tags[tag].append(img)
            else:
                tags[tag] = [img]


if __name__ == '__main__':
    EMULATE = True
    tags, image_specs = {}, {}
    internal_states = {
        'settings': {'gain': 150, 'offset': 0, 'exposure': 100000, 'interval': 0},
        'current_tag': None,
        'displaying_list': scan_images(),
        'eta': "",
    }
    restore_png()

    cam: Optional[camera.Camera] = None
    load_specs()

    try:
        cam = camera.Camera(PROJECT_PATH, EMULATE)
        settings = {'gain': 150, 'offset': 0, 'exposure': 100000, 'interval': 0}
        app.run(host='0.0.0.0', port=8080)
    finally:
        if scheduler is not None:
            terminate_scheduler.set()
            scheduler.join()
        cam.close()
        print("Server closed")
