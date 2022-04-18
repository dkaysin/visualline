from sortedcontainers import SortedKeyList
import requests as req
import asyncio as aio
import httpx
import time
import math

from Media import Media, parse_media

MAX_SIMULT_REQUESTS = 10
FB_GRAPH_URL = "https://graph.instagram.com"


def _fetch_user_name(user_id: str, access_token: str) -> dict:
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


def _fetch_user_media(_user_id: str, access_token: str) -> dict:
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


async def get_media_list(user_id: str, access_token: str, CANVAS_HEIGHT: int) -> [Media]:
    response = _fetch_user_media(user_id, access_token)
    # print(response)
    if "error" in response:
        raise IOError('Received error while fetching user media:', response)
    if "data" not in response:
        return SortedKeyList([])
    data = response["data"]

    client = httpx.AsyncClient()
    tasks = []

    sem = aio.Semaphore(MAX_SIMULT_REQUESTS)
    for media in data:
        tasks.append(aio.create_task(parse_media(sem, client, media, CANVAS_HEIGHT)))

    while response.get("paging").get("next") is not None:
        response = req.get(response["paging"]["next"]).json()
        data = response.get("data")
        for media in data:
            tasks.append(aio.create_task(parse_media(sem, client, media, CANVAS_HEIGHT)))

    res = await aio.gather(*tasks)
    await client.aclose()
    res = [m for m in res if m is not None]
    res = sorted(res, key=lambda m: m.strip_position)
    res = _generate_strip_positions(res)
    print("Collected media: ", len(res))
    return res


def _generate_strip_positions(media_list: [Media]) -> [Media]:
    for i, media in enumerate(media_list):
        if i == 0:
            media.strip_position = 0
        else:
            prev_media = media_list[i-1]
            delta = media.timestamp - prev_media.timestamp
            # delta_log = min(delta, 60*60*24*10) ** 0.25
            delta_log = (1+math.log(1+delta))**1.5
            media.strip_position = prev_media.strip_position + delta_log
    return media_list

