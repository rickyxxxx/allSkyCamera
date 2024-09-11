import io
import os
import zipfile

from flask import Flask, send_from_directory, render_template, request, jsonify, send_file


# check and initialize the project path
try:
    PROJECT_PATH = os.environ["ALL_SKY_CAMERA"]
except KeyError:
    raise RuntimeError("Please set the environment variable ALL_SKY_CAMERA to the project path !!!")


app = Flask(__name__)
PATH = "../shared/img/"


def get_image_files(folder):
    return sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])

GAIN, OFFSET, EXPOSURE, INTERVAL = 10, 140, 20_000, 3

@app.route('/')
def index():
    global GAIN, OFFSET, EXPOSURE, INTERVAL
    with open("../../shared/settings.txt", "r") as f:
        settings = f.read()

    GAIN, OFFSET, EXPOSURE, INTERVAL = settings.split(" ")
    EXPOSURE = f"{int(EXPOSURE):,}"
    print(f"Settings: {GAIN} {OFFSET} {EXPOSURE} {INTERVAL}")
    return render_template('../html/index.html') % (EXPOSURE, GAIN, OFFSET, INTERVAL)

@app.route('/images')
def images():
    convert_images()
    images = get_image_files(PATH)
    return jsonify(images)

@app.route('/submit', methods=['POST'])
def submit():
    global GAIN, OFFSET, EXPOSURE, INTERVAL
    EXPOSURE = request.form.get('field1')
    GAIN = request.form.get('field2')
    OFFSET = request.form.get('field3')
    INTERVAL = request.form.get('field4')
    content = GAIN + " " + OFFSET + " " + EXPOSURE.replace(",", "") + " " + INTERVAL
    with open("../shared/settings.txt", "w") as f:
        f.write(content)
    return jsonify(success=True)

@app.route('/allSkyCamera/shared/img/<path:filename>')
def data(filename):
    return send_from_directory('../shared/img/', filename)

@app.route('/download_images')
def download_images():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in get_image_files(PATH):
            zf.write(os.path.join(PATH, filename), filename)
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name='images.zip')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)