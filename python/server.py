from flask import Flask, send_from_directory, render_template_string
import os

app = Flask(__name__)

def get_image_files(folder):
    return [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]

def generate_html(images):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Gallery</title>
    </head>
    <body>
        <h1>Image Gallery</h1>
        <div style='display: flex; flex-wrap: wrap;'>
    """
    for image in images:
        html += f"<div style='margin: 10px;'><img src='/data/{image}' style='max-width: 200px; max-height: 200px;'></div>"
    html += """
        </div>
    </body>
    </html>
    """
    return html

@app.route('/')
def index():
    images = get_image_files('../data')
    html = generate_html(images)
    return render_template_string(html)

@app.route('/data/<path:filename>')
def data(filename):
    return send_from_directory('./data', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)