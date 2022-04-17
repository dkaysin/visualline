from sortedcontainers import SortedList, SortedKeyList
import random
from skimage import exposure, filters, io
import imageio.v3 as iio
import requests as req
import asyncio as aio
import httpx
import time

from Media import Media, parse_media


FB_GRAPH_URL = "https://graph.instagram.com"


def _fetch_user_name(client, user_id: str, access_token: str) -> dict:
    fields = {
        "fields": "id,username,media_count",
        "access_token": access_token
    }
    try:
        response = req.get(f"{FB_GRAPH_URL}/me", params=fields).json()
    except req.exceptions.ConnectionError as err:
        return {
            "error": err
        }
    return response


def _fetch_user_media(client, _user_id: str, access_token: str) -> dict:
    fields = {
        "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
        "access_token": access_token
    }
    try:
        response = req.get(f"{FB_GRAPH_URL}/me/media", params=fields).json()
    except req.exceptions.ConnectionError as err:
        return {
            "error": err
        }
    return response


async def get_media_list(user_id: str, access_token: str) -> [Media]:
    start_time = time.time()
    client = httpx.AsyncClient()
    response = _fetch_user_media(client, user_id, access_token)
    print(response)
    if "error" in response:
        raise IOError('Received error while fetching user media:', response)
    if "data" not in response:
        return SortedKeyList([])
    data = response["data"]

    futures = [parse_media(client, media) for media in data]
    res = await aio.gather(*futures)
    print("<get_media_list> execution time: --- %s seconds ---" % (time.time() - start_time))
    return [m for m in res if m is not None]
