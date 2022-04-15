from flask import Flask, send_file
from main import dataset, get_strips, draw, render
import os

app = Flask(__name__)


@app.route("/")
def hello_world():
    images, timestamps = dataset()
    strips = get_strips(images)
    canvas = draw(strips, timestamps)
    render(canvas)

    # return "<p>Hello, World!</p>"
    image = os.path.join('./out.jpg')
    return send_file(image, mimetype='image/jpg')
