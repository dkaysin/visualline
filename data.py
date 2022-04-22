from sortedcontainers import SortedKeyList
import asyncio as aio
import httpx
import math
from flask import g

from Media import Media, parse_media

MAX_SIMULT_REQUESTS = 10
FB_GRAPH_URL = "https://graph.instagram.com"


async def get_media_list(CANVAS_HEIGHT: int, user_id: str, access_token: str) -> [Media]:
    client = httpx.AsyncClient()

    fields = {
        "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
        "access_token": access_token
    }
    response = (await client.get(f"{FB_GRAPH_URL}/me/media", params=fields)).json()

    if "error" in response:
        raise IOError('Received error while fetching user media:', response)
    if "data" not in response:
        raise IOError('No data is provided.', response)
    data = response["data"]
    db_cur = g.db_conn.cursor()
    tasks = []
    sem = aio.Semaphore(MAX_SIMULT_REQUESTS)
    for media in data:
        tasks.append(aio.create_task(parse_media(db_cur, sem, client, CANVAS_HEIGHT, media)))
    while response.get("paging").get("next") is not None:
        response = (await client.get(response["paging"]["next"])).json()
        data = response.get("data")
        for media in data:
            tasks.append(aio.create_task(parse_media(db_cur, sem, client, CANVAS_HEIGHT, media)))

    res = await aio.gather(*tasks)
    db_cur.close()
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
            delta_log = (1+math.log(1+delta))**1.5
            media.strip_position = prev_media.strip_position + delta_log
    return media_list
