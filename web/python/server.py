import os
import json
from typing import Iterable

from flask import Flask, send_from_directory, render_template, request, jsonify, send_file

# check and initialize the project path
try:
    PROJECT_PATH = os.environ["ALL_SKY_CAMERA"]
    print(f"Project path loaded: {PROJECT_PATH}")
except KeyError:
    raise RuntimeError("Please set the environment variable ALL_SKY_CAMERA to the project path !!!")

# configure the Flask server
app = Flask(__name__, static_folder=f"{PROJECT_PATH}/shared", template_folder=f"{PROJECT_PATH}/web/html")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/images')
def images():
    with open(f"{PROJECT_PATH}/shared/img/image_info.json") as spec:
        img_specs = json.load(spec)

    def unpack_specs(f: str) -> Iterable:
        fields = "timestamp", "exposure", "gain", "offset", "star"
        return [img_specs[f][field] for field in fields]

    def is_image(f: str) -> bool:
        suffixes = '.jpg', '.png', '.jpeg'
        return any(f.endswith(suffix) for suffix in suffixes)

    img_w_specs = [
        (f, *unpack_specs(f))
        for f in os.listdir(f"{PROJECT_PATH}/shared/img")
        if is_image(f)
    ]

    print(img_w_specs)
    return jsonify(img_w_specs)


@app.route("/star", methods=['POST'])
def star():
    with open(f"{PROJECT_PATH}/shared/img/image_info.json") as spec:
        img_specs = json.load(spec)
    current_state = img_specs[request.json["image"]]['star']
    new_state = 1 - current_state
    img_specs[request.json["image"]]['star'] = new_state
    with open(f"{PROJECT_PATH}/shared/img/image_info.json", "w") as spec:
        json.dump(img_specs, spec)
    return jsonify(success=True)


# @app.route('/submit', methods=['POST'])
# def submit():
#     global GAIN, OFFSET, EXPOSURE, INTERVAL
#     EXPOSURE = request.form.get('field1')
#     GAIN = request.form.get('field2')
#     OFFSET = request.form.get('field3')
#     INTERVAL = request.form.get('field4')
#     content = GAIN + " " + OFFSET + " " + EXPOSURE.replace(",", "") + " " + INTERVAL
#     with open("../shared/settings.txt", "w") as f:
#         f.write(content)
#     return jsonify(success=True)
#
#
# @app.route('/allSkyCamera/shared/img/<path:filename>')
# def data(filename):
#     return send_from_directory('../shared/img/', filename)
#
#
# @app.route('/download_images')
# def download_images():
#     memory_file = io.BytesIO()
#     with zipfile.ZipFile(memory_file, 'w') as zf:
#         for filename in get_image_files(PATH):
#             zf.write(os.path.join(PATH, filename), filename)
#     memory_file.seek(0)
#     return send_file(memory_file, as_attachment=True, download_name='images.zip')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
