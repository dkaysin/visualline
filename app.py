from flask import Flask, send_file, request, session, redirect, url_for
import imageio.v3 as iio
import io
import requests as req
from os import environ
from markupsafe import escape
from sortedcontainers import SortedList, SortedKeyList
import asyncio as aio
import time

from draw import draw, save_on_disk
from data import get_media_list

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 800


app = Flask(__name__)
app.secret_key = b'sf423ef24378y'  # TODO replace with dynamically generated key on a per-person basis

APP_ID = "1113503899492527"
FB_VISUALLINE_APP_SECRET = environ.get('FB_VISUALLINE_APP_SECRET')
APP_URL = "https://visualline.herokuapp.com"
AUTH_REDIRECT_URL = APP_URL+"/auth/"
FB_AUTH_URL = "https://api.instagram.com/oauth/authorize"
FB_ACCESS_TOKEN_URL = "https://api.instagram.com/oauth/access_token"


import gc
import os
import tracemalloc
import psutil
process = psutil.Process(os.getpid())
tracemalloc.start()
s = None


@app.route("/memory")
def print_memory():
    return {
        "memory": process.memory_info().rss,
        }


@app.route("/snapshot")
def snap():
    global s
    if not s:
        s = tracemalloc.take_snapshot()
        return "taken snapshot\n"
    else:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        compared = snapshot.compare_to(s, 'lineno')
        return f"""
            <p>Top stats:</p>
            {"".join([f"<p> {str(line)} </p>" for line in top_stats[:10]])}
            <br/>
            <p>Compared:</p>
            {"".join([f"<p> {str(line)} </p>" for line in compared[:10]])}
        """



# TODO move to frontend
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
async def serve_image():
    start_time = time.time()
    style = request.args.get('style')
    if style is None:
        style = 0
    else:
        style = int(style)

    # if ('user_id' not in session) or ('access_token' not in session):
    #     return {
    #         "error_type": "AuthRequired",
    #         "error_message": "User is not authenticated"
    #     }
    # user_id = session['user_id']
    # access_token = session['access_token']

    user_id = "17841400819370683"
    access_token = "IGQVJVdWtid3ZAtQnNEb2pxVkgyajNLQlVpZAFBNcFBvVzczNkRUWjFTSlFMY1QyeU9JbEtWWE5DOHpTSm1Cc3JLUmJGbFVlaGd2SjV4Q0txYjN2MVp6T3lpN3NLRkZAYQUpIMHBfTkhpeFhfRFIzdFpCUAZDZD"


    print("preparation time: --- %s seconds ---" % (time.time() - start_time))

    start_time = time.time()
    media_list = SortedKeyList(
        await get_media_list(user_id, access_token, CANVAS_HEIGHT),
        key=lambda m: m.strip_position
    )
    print("<get_media_list> execution time: --- %s seconds ---" % (time.time() - start_time))

    start_time = time.time()
    canvas = draw(media_list, CANVAS_WIDTH, CANVAS_HEIGHT, style)
    print("<draw> execution time: --- %s seconds ---" % (time.time() - start_time))

    start_time = time.time()
    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpg")
    output.seek(0)
    gc.collect()
    print("image delivery execution time: --- %s seconds ---" % (time.time() - start_time))
    return send_file(output, mimetype='image/jpg')


if __name__ == '__main__':
    print('Hello world!')
    # image = serve_image()
