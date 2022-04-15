from flask import Flask, send_file, request
import imageio.v3 as iio
import io

from process import get_strips, draw, render
from data import sample_dataset, get_data

app = Flask(__name__)

APP_ID = 321034639960041
REDIRECT_URL = "https://visualline.herokuapp.com/auth/"


# This will be moved to frontend
@app.route("/login/")
def request_login():
    request = "https://api.instagram.com/oauth/authorize" + \
        f"?client_id = {APP_ID}" + \
        f"& redirect_uri = {REDIRECT_URL}" + \
        "& scope = user_profile, user_media" + \
        "& response_type = code"
    # send request


@app.route("/auth/<code>")
def auth():
    code = request.args.get('code')
    print(code)
    return f"<html> Your short lived auth code is: {code}</html>"


# @app.route("/", methods=['GET'])
@app.route("/")
def serve_image():
    # account_name = request.args.get('acc')

    # images, timestamps = get_data(account_name)
    images, timestamps = get_data("")
    strips = get_strips(images)
    canvas = draw(strips, timestamps)

    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpg")
    output.seek(0)
    return send_file(output, mimetype='image/jpg')


if __name__ == '__main__':
    print('Hello world!')
    # image = serve_image()