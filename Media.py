from skimage import exposure, filters, io
from skimage.util import img_as_ubyte, img_as_float
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
import numpy as np
from sortedcontainers import SortedKeyList
from datetime import datetime
import imageio.v3 as iio
import asyncio as aio
import httpx

CANVAS_HEIGHT = 1000
STRIP_BLUR_RADIUS = CANVAS_HEIGHT / 20


async def parse_media(session, payload):
    media = Media(payload)
    if media.media_type in ["IMAGE", "CAROUSEL_ALBUM"]:
        url = payload.get('media_url')
        image = None
        tries = 0
        while (image is None) and (tries < 5):
            tries += 1
            try:
                print("Fetching image from url. Media id: ", media.media_id)
                response = await session.get(url)
                img_bytes = response.content
                image = img_as_float(iio.imread(img_bytes))
            except:  # TODO more specific exception must be used
                await aio.sleep(0.1)
        media.strip = generate_strip(image)
        return media
    return None


class Media:
    def __init__(self, payload):
        self.media_type = payload.get('media_type')
        self.media_id = payload.get('id')
        self.caption = payload.get('caption')
        self.media_type = payload.get('media_type')
        self.permalink = payload.get('permalink')
        self.username = payload.get('username')
        dt = datetime.strptime(payload['timestamp'], "%Y-%m-%dT%H:%M:%S%z")
        self.timestamp = dt.timestamp()
        self.media_url = payload.get('media_url')
        self.strip = None


def generate_strip(image: np.array) -> np.array:
    if image is None:
        return None
    strip = np.median(image, axis=1)
    if image.shape[0] != CANVAS_HEIGHT:
        strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1))
    strip = ndi.gaussian_filter1d(strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    return strip


# if __name__ == '__main__':
#     pass

