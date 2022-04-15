from flask import Flask, send_file, request
import imageio.v3 as iio
import io

from process import get_strips, draw, render
from data import sample_dataset, get_data

app = Flask(__name__)


# @app.route("/", methods=['GET'])
@app.route("/")
def serve_image():
    # account_name = request.args.get['acc']

    # images, timestamps = get_data(account_name)
    images, timestamps = get_data("")
    strips = get_strips(images)
    canvas = draw(strips, timestamps)

    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpg")
    output.seek(0)
    return send_file(output, mimetype='image/jpg')


# if __name__ == '__main__':
#     # print('Test')
#     image = serve_image()