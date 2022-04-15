from flask import Flask, send_file, request, session
import imageio.v3 as iio
import io
import requests as req
from os import environ
from markupsafe import escape


from process import get_strips, draw, render
from data import sample_dataset, get_data

app = Flask(__name__)
app.secret_key = b'sf423ef24378y'

APP_ID = "1113503899492527"
FB_VISUALLINE_APP_SECRET = environ.get('FB_VISUALLINE_APP_SECRET')
APP_URL = "https://visualline.herokuapp.com/"
AUTH_REDIRECT_URL = APP_URL+"auth/"
FB_AUTH_URL = "https://api.instagram.com/oauth/authorize"
FB_ACCESS_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
FB_GRAPH_URL = "https://graph.instagram.com/"


# Initialize SQLite3


# This will be moved to frontend
@app.route("/login/")
def request_login():
    href = f"""{FB_AUTH_URL}
        ?client_id={APP_ID}
        &redirect_uri={AUTH_REDIRECT_URL}
        &scope=user_profile,user_media"
        &response_type=code"""
    return f"<html> <a href={href}> Click to login </a> </html>"


@app.route("/auth/")
def auth():
    code = escape(request.args.get('code'))
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
    # Save user's credentials in session storage
    session['user_id'] = response['user_id']
    session['access_token'] = response['access_token']
    return f"<html> Authentication is complete</html>"

@app.route("/")
def index():
    return f"""
        <html>
            <a href="{APP_URL}fetch/">/fetch/</a> <br/>
            <a href="{APP_URL}login/">/login/</a> <br/>
            <a href="{APP_URL}auth/">/auth/</a>
        </html>
        """


@app.route("/fetch/")
def serve_image():
    # account_name = request.args.get('acc')

    # if 'user_id' in session:
    #     return f'Logged in as {session["username"]}'
    # return 'You are not logged in'

    # images, timestamps = get_data(account_name)
    images, timestamps = get_data("")
    strips = get_strips(images)
    canvas = draw(strips, timestamps)

    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpg")
    output.seek(0)
    return send_file(output, mimetype='image/jpg')


def fetch_data():
    user_id = ""
    access_token = ""
    r = f"""{FB_GRAPH_URL}/{user_id}?
        fields=id,username
        &access_token={access_token}"""


if __name__ == '__main__':
    print('Hello world!')
    # image = serve_image()