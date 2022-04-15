from flask import Flask, send_file, request
import imageio.v3 as iio
import io
import requests as req
from os import environ


from process import get_strips, draw, render
from data import sample_dataset, get_data

app = Flask(__name__)

APP_ID = "1113503899492527"
FB_VISUALLINE_APP_SECRET = environ.get('FB_VISUALLINE_APP_SECRET')
AUTH_REDIRECT_URL = "https://visualline.herokuapp.com/auth/"
FB_AUTH_URL = "https://api.instagram.com/oauth/access_token"


# This will be moved to frontend
@app.route("/login/")
def request_login():
    href = "https://api.instagram.com/oauth/authorize" + \
        f"?client_id={APP_ID}" + \
        f"&redirect_uri={AUTH_REDIRECT_URL}" + \
        "&scope=user_profile,user_media" + \
        "&response_type=code"
    return f"<html> <a href={href}> Click to login </a> </html>"


@app.route("/auth/")
def auth():
    code = request.args.get('code')
    fields = {
        'client_id': APP_ID,
        'client_secret': FB_VISUALLINE_APP_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': AUTH_REDIRECT_URL,
        'code': code
    }
    response = req.post(FB_AUTH_URL, data=fields)
    print(response)
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