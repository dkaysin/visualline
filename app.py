from flask import Flask, send_file
from main import dataset, get_strips, draw, render
import imageio.v3 as iio
import io

app = Flask(__name__)


@app.route("/")
def serve_image():
    images, timestamps = dataset()
    strips = get_strips(images)
    canvas = draw(strips, timestamps)
    # render(canvas)

    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpeg")
    return send_file(output, mimetype='image/jpeg')


# if __name__ == '__main__':
#     # print('Test')
#     image = serve_image()