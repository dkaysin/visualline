from flask import Flask, send_file, request, session, redirect, url_for, g, jsonify
import imageio.v3 as iio
import io
import os
from markupsafe import escape
from sortedcontainers import SortedKeyList
import time
import httpx
import psycopg2
from psycopg2 import pool
import asyncio as aio

from draw import draw, save_on_disk
from data import get_media_list

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 800
DEBUG_MODE = os.environ.get("DEBUG_MODE") == "True"

app = Flask(__name__)

app.secret_key = os.environ.get("APP_SECRET_KEY")

APP_ID = "1113503899492527"
FB_VISUALLINE_APP_SECRET = os.environ.get("FB_VISUALLINE_APP_SECRET")
APP_URL = "https://visualline.herokuapp.com"
AUTH_REDIRECT_URL = APP_URL+"/auth/"
FB_AUTH_URL = "https://api.instagram.com/oauth/authorize"
FB_ACCESS_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DATABASE_URL = os.environ.get('DATABASE_URL')


# app.config["static_url_path"] = "/frontend/visualline/build"

if DEBUG_MODE:
    app.config['postgreSQL_pool'] = pool.SimpleConnectionPool(1, 20,
                                                              dbname='visualline-db',
                                                              user=DB_USER,
                                                              password=DB_PASSWORD)
else:
    app.config['postgreSQL_pool'] = pool.SimpleConnectionPool(1, 20, DATABASE_URL, sslmode='require')


def get_db_conn():
    if 'db' not in g:
        g.db_conn = app.config['postgreSQL_pool'].getconn()
    return g.db_conn


@app.teardown_appcontext
def close_conn(e):
    db = g.pop('db', None)
    if db is not None:
        app.config['postgreSQL_pool'].putconn(db)


import os
import gc
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
async def auth():
    client = httpx.AsyncClient()
    code = request.args.get('code')
    if code is None:
        return {
            "error_type": "AuthException",
            "error_message": "Please provide correct short-lived code for FB authentication"
        }

    # code = escape(code)
    fields = {
        'client_id': APP_ID,
        'client_secret': FB_VISUALLINE_APP_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': AUTH_REDIRECT_URL,
        'code': code
    }
    response = (await client.post(FB_ACCESS_TOKEN_URL, data=fields)).json()
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
    return app.send_static_file("index.html")


    # return f"""
    #     <html>
    #         <a href="{APP_URL}/fetch/">/fetch/</a> <br/>
    #         <a href="{APP_URL}/login/">/login/</a> <br/>
    #         <a href="{APP_URL}/auth/">/auth/</a> <br/>
    #         <a href="{APP_URL}/de_auth/">/de-auth/</a>
    #     </html>
    #     """


@app.route("/is_logged_in/")
async def is_logged_in():
    await aio.sleep(1)
    response = jsonify({"isLoggedIn": ('user_id' in session and 'access_token' in session)})
    # response = jsonify({"isLoggedIn": True})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@app.route("/fetch/")
async def serve_image():
    style = request.args.get('style')
    if style is None:
        style = 0
    else:
        style = int(style)

    start_time = time.time()
    if DEBUG_MODE:
        user_id = os.environ.get('DEBUG_USER_ID')
        access_token = os.environ.get('DEBUG_ACCESS_TOKEN')
    else:
        if 'user_id' not in session or 'access_token' not in session:
            return {
                "error_type": "AuthRequired",
                "error_message": "User is not authenticated"
            }
        user_id = session['user_id']
        access_token = session['access_token']
    print("authentication execution time: --- %s seconds ---" % (time.time() - start_time))

    start_time = time.time()
    # db_conn = psycopg2.connect(f"dbname=visualline-db user={DB_USER} password={DB_PASSWORD}")
    db_conn = get_db_conn()
    media_list = SortedKeyList(
        await get_media_list(CANVAS_HEIGHT, user_id, access_token),
        key=lambda m: m.strip_position
    )
    db_conn.commit()
    print("<get_media_list> execution time: --- %s seconds ---" % (time.time() - start_time))

    start_time = time.time()
    canvas = draw(media_list, CANVAS_WIDTH, CANVAS_HEIGHT, style)
    print("<draw> execution time: --- %s seconds ---" % (time.time() - start_time))

    start_time = time.time()
    output = io.BytesIO()
    iio.imwrite(output, canvas, format_hint=".jpg")
    output.seek(0)
    db_conn.close()
    gc.collect()
    print("image delivery execution time: --- %s seconds ---" % (time.time() - start_time))
    response = send_file(output, mimetype='image/jpg')
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


if __name__ == '__main__':
    print('Hello world!')
    # image = serve_image()
