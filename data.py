from sortedcontainers import SortedList, SortedKeyList
import random
from skimage import exposure, filters, io
import imageio.v3 as iio
import requests as req

from Media import Media, parse_media


FB_GRAPH_URL = "https://graph.instagram.com"


def _fetch_user_name(user_id: str, access_token: str) -> dict:
    fields = {
        "fields": "id,username,media_count",
        "access_token": access_token
    }
    response = req.get(f"{FB_GRAPH_URL}/me", params=fields).json()
    return response


def _fetch_user_media(_user_id: str, access_token: str) -> dict:
    fields = {
        "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
        "access_token": access_token
    }
    response = req.get(f"{FB_GRAPH_URL}/me/media", params=fields).json()
    return response


def get_media_list(user_id: str, access_token: str) -> SortedKeyList[Media]:
    response = _fetch_user_media(user_id, access_token)
    if "data" not in response:
        return SortedKeyList([])
    data = response["data"]
    return SortedKeyList(
        (x for x in (parse_media(media) for media in data) if x is not None),
        key=(lambda m: m.timestamp)
    )


# def sample_dataset():
#     _images = io.ImageCollection('./dataset/*.jpg')
#     print("Length of dataset:", len(_images))
#     base_ts = 1331856000
#     _timestamps = SortedList([base_ts + t * random.uniform(1, 1.3) * 100000 for t in range(len(_images))])
#     return _images, _timestamps
