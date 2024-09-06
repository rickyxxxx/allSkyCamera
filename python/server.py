from flask import Flask, send_from_directory, render_template_string, request, jsonify, send_file
import os
import zipfile
import io

from python.plot import convert_images

app = Flask(__name__)
PATH = "../shared/img/"

def get_image_files(folder):
    return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

with open("../shared/settings.txt", "r") as f:
    settings = f.read()

GAIN, OFFSET, EXPOSURE, INTERVAL = settings.split(" ")
EXPOSURE = f"{int(EXPOSURE):,}"

@app.route('/')
def index():
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
                            div.innerHTML = `<img src='allSkyCamera/shared/img/${image}'><br><span>${image}</span>`;
                            gallery.appendChild(div);
                        });
                    });
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

            setFieldValues('%s', '%s', '%s', '%s');

            document.getElementById('downloadButton').addEventListener('click', function() {
                window.location.href = '/download_images';
            });

            setInterval(fetchImages, 5000);
            fetchImages();
        </script>
    </body>
    </html>
    """ % (EXPOSURE, GAIN, OFFSET, INTERVAL))

@app.route('/images')
def images():
    convert_images()
    images = get_image_files(PATH)
    return jsonify(images)

@app.route('/submit', methods=['POST'])
def submit():
    field1 = request.form.get('field1')
    field2 = request.form.get('field2')
    field3 = request.form.get('field3')
    field4 = request.form.get('field4')
    content = field2 + " " + field3 + " " + field1.replace(",", "") + " " + field4
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