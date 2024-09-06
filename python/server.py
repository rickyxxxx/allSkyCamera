from flask import Flask, send_from_directory, render_template_string, request, jsonify, send_file
import os
import zipfile
import io
import tqdm
import numpy as np
from PIL import Image

def convert_images():
    binary_files = os.listdir("../shared/bin")

    for file in tqdm.tqdm(binary_files):
        try:
            data = np.fromfile(f"../shared/bin/{file}", dtype=np.uint16).reshape(2180, 3856)
            image = Image.fromarray(data)
            image.save(f"../shared/img/{file.replace('.bin', '.tif')}")
            os.remove(f"../shared/bin/{file}")
        except ValueError:
            print(f"File {file} is not a valid binary file. Skipping...")
app = Flask(__name__)
PATH = "../shared/img/"

def get_image_files(folder):
    return sorted([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])


GAIN, OFFSET, EXPOSURE, INTERVAL = 10, 140, 20_000, 3

@app.route('/')
def index():
    global GAIN, OFFSET, EXPOSURE, INTERVAL
    with open("../shared/settings.txt", "r") as f:
        settings = f.read()

    GAIN, OFFSET, EXPOSURE, INTERVAL = settings.split(" ")
    EXPOSURE = f"{int(EXPOSURE):,}"
    print(f"Settings: {GAIN} {OFFSET} {EXPOSURE} {INTERVAL}")
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Gallery</title>
        <style>
            body { display: flex; }
            #panel { width: 200px; padding: 10px; border-right: 1px solid #ccc; }
            #gallery { flex-grow: 1; padding: 10px; display: flex; flex-wrap: wrap; }
            .image { margin: 10px; text-align: center; }
            .image img { max-width: 200px; max-height: 200px; display: block; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div id="panel">
            <h2>Input Panel</h2>
            <form id="inputForm">
                <label for="field1">Exposure Time (us):</label><br>
                <input type="text" id="field1" name="field1"><br>
                <label for="field2">Gain:</label><br>
                <input type="text" id="field2" name="field2"><br>
                <label for="field3">Offset:</label><br>
                <input type="text" id="field3" name="field3"><br>
                <label for="field4">Interval (s):</label><br>
                <input type="text" id="field4" name="field4"><br><br>
                <button type="submit">Submit</button>
            </form>
            <button id="downloadButton">Download All Images</button>
        </div>
        <div id="gallery"></div>
        <script>
            function fetchImages() {
                fetch('/images')
                    .then(response => response.json())
                    .then(images => {
                        const gallery = document.getElementById('gallery');
                        gallery.innerHTML = '';
                        images.forEach(image => {
                            const div = document.createElement('div');
                            div.className = 'image';
                            div.innerHTML = `<img src='allSkyCamera/shared/img/${image}' onclick='displayFullScreen(this)'><br><span>${image}</span>`;
                            gallery.appendChild(div);
                        });
                    });
            }

            function displayFullScreen(imgElement) {
                const fullScreenDiv = document.createElement('div');
                fullScreenDiv.style.position = 'fixed';
                fullScreenDiv.style.top = '0';
                fullScreenDiv.style.left = '0';
                fullScreenDiv.style.width = '100%ds';
                fullScreenDiv.style.height = '100%ds';
                fullScreenDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
                fullScreenDiv.style.display = 'flex';
                fullScreenDiv.style.justifyContent = 'center';
                fullScreenDiv.style.alignItems = 'center';
                fullScreenDiv.style.zIndex = '1000';
                fullScreenDiv.onclick = function() {
                    document.body.removeChild(fullScreenDiv);
                };

                const fullScreenImg = document.createElement('img');
                fullScreenImg.src = imgElement.src;
                fullScreenImg.style.maxWidth = '100%ds';
                fullScreenImg.style.maxHeight = '100%ds';

                fullScreenDiv.appendChild(fullScreenImg);
                document.body.appendChild(fullScreenDiv);
            }

            document.getElementById('inputForm').addEventListener('submit', function(event) {
                event.preventDefault();
                const formData = new FormData(event.target);
                fetch('/submit', {
                    method: 'POST',
                    body: formData
                }).then(response => response.json())
                  .then(data => {
                      alert('Form submitted successfully');
                  });
            });

            // Function to set the values of the input fields
            function setFieldValues(field1Value, field2Value, field3Value, field4Value) {
                document.getElementById('field1').value = field1Value;
                document.getElementById('field2').value = field2Value;
                document.getElementById('field3').value = field3Value;
                document.getElementById('field4').value = field4Value;
            }

            setFieldValues(exposure_, gain_, offset_, interval_);

            document.getElementById('downloadButton').addEventListener('click', function() {
                window.location.href = '/download_images';
            });

            setInterval(fetchImages, 5000);
            fetchImages();
        </script>
    </body>
    </html>
    """.replace("exposure_", EXPOSURE).replace("gain_", GAIN).replace("offset_", OFFSET).replace("interval_", INTERVAL))

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