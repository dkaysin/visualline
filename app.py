from flask import Flask, send_file, request, session, redirect, url_for
import imageio.v3 as iio
import io
import requests as req
from os import environ
from markupsafe import escape

from draw import draw
from data import get_media_list


app = Flask(__name__)
app.secret_key = b'sf423ef24378y'  # TODO replace with dynamically generated key

APP_ID = "1113503899492527"
FB_VISUALLINE_APP_SECRET = environ.get('FB_VISUALLINE_APP_SECRET')
APP_URL = "https://visualline.herokuapp.com"
AUTH_REDIRECT_URL = APP_URL+"/auth/"
FB_AUTH_URL = "https://api.instagram.com/oauth/authorize"
FB_ACCESS_TOKEN_URL = "https://api.instagram.com/oauth/access_token"


# Initialize SQLite3


# This will be moved to frontend
@app.route("/login/")
def request_login():
    href = f"{FB_AUTH_URL}" + \
        f"?client_id={APP_ID}" + \
        f"&redirect_uri={AUTH_REDIRECT_URL}" + \
        f"&scope=user_profile,user_media" + \
        f"&response_type=code"
    return f"<html> <a href={href}> Click to login </a> </html>"


@app.route("/auth/")
def auth():
    code = request.args.get('code')
    if code is None:
        return {
            "error_type": "AuthException",
            "error_message": "Please provide correct short-lived code for FB authentication"
        }

    code = escape(code)
    fields = {
        'client_id': APP_ID,
        'client_secret': FB_VISUALLINE_APP_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': AUTH_REDIRECT_URL,
        'code': code
    }
    response = req.post(FB_ACCESS_TOKEN_URL, data=fields).json()
    print("Auth response:")
    print(response)

    if ('user_id' not in response) or ('access_token' not in response):
        return {
            "error_type": "FBAuthException",
            "error_message": "Authentication with FB failed",
            "data": response
        }

    # Save user's credentials in session storage
    session['user_id'] = response['user_id']
    session['access_token'] = response['access_token']
    return redirect(url_for('index'))


@app.route("/de_auth/")
def de_auth():
    session.pop('user_id', None)
    session.pop('access_token', None)
    return redirect(url_for('index'))


@app.route("/")
def index():
    return f"""
        <html>
            <a href="{APP_URL}/fetch/">/fetch/</a> <br/>
            <a href="{APP_URL}/login/">/login/</a> <br/>
            <a href="{APP_URL}/auth/">/auth/</a> <br/>
            <a href="{APP_URL}/de_auth/">/de-auth/</a> 
        </html>
        """


@app.route("/fetch/")
def serve_image():
    # if ('user_id' not in session) or ('access_token' not in session):
    #     return {
    #         "error_type": "AuthRequired",
    #         "error_message": "User is not authenticated"
    #     }

    user_id = ""
    access_token = "AQCMpXl4ivQH1HaluyUhFGhRl1rV1UPclnJrQvTZerGW40vJkChiGKY3y6p3rr1Ws_PHMDF2p65T8ELcdfRbtuB5V5zhmILUManshUmJD8UYvYszumOPpDKicFGg76BUVmh_UO09tlSYi_jGxQmBefd89ufAvhLkGVRqAcyiecIww-LExBFh1dIFx7X91xUsIYTa9Q7wVn1Vl6JKu7iVDdlNuGS6grxBGySS9uJyoMfSOg"

    # user_id = session['user_id']
    # access_token = session['access_token']
    media_list = get_media_list(user_id, access_token)
    canvas = draw(media_list)

    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpg")
    output.seek(0)
    return send_file(output, mimetype='image/jpg')


if __name__ == '__main__':
    print('Hello world!')
    # image = serve_image()
