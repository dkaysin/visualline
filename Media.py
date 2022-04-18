from skimage.util import img_as_ubyte, img_as_float
from scipy import ndimage as ndi
import numpy as np
from datetime import datetime
import imageio.v3 as iio
import asyncio as aio
from more_itertools import chunked

from PIL import Image


async def parse_media(sem, client, payload, CANVAS_HEIGHT):
    media = Media(payload)
    if media.media_type in ["IMAGE", "CAROUSEL_ALBUM"]:
        url = payload.get('media_url')
        image = None
        tries = 0
        async with sem:
            while (image is None) and (tries <= 5):
                tries += 1
                # print(f"Fetching media {media.media_id} from {media.media_url}. Try: {tries}")
                try:
                    response = await client.get(url)
                    img_bytes = response.content
                    image = iio.imread(img_bytes)
                    # image = img_as_float(iio.imread(img_bytes))
                except Exception:  # TODO more specific exception must be used
                    # await aio.sleep(0.1 * 2**tries)
                    await aio.sleep(0.1)
            if image is not None:
                media.strip = generate_strip(image, CANVAS_HEIGHT)
                return media
    print(f"Media {media.media_id} skipped: ", media.media_id)
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
        self.strip_position = self.timestamp
        self.media_url = payload.get('media_url')
        self.strip = None

    def __str__(self):
        return f"id: {self.media_id}, Timestamp: {self.timestamp}, strip_position: {self.strip_position}, strip: {self.strip}"


def generate_strip(image: np.array, CANVAS_HEIGHT: int) -> np.array:
    if image is None:
        raise ValueError("Image provided to generate_strip is None")

    # subsampling = int(image.shape[1] / 200)
    # image = img_as_float(image)
    # strip = np.median(image[::subsampling, ::subsampling, ::], axis=1)
    # if strip.shape[0] != CANVAS_HEIGHT:
    #     strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1), order=1)
    # strip_blur_radius = CANVAS_HEIGHT / 20
    # strip = ndi.gaussian_filter1d(strip, sigma=strip_blur_radius, axis=0)

    thumbnail = ndi.zoom(image, (150/image.shape[0], 500/image.shape[0], 1), order=1)
    strip = np.array([_get_dominant_color(np.array(chunk)) for chunk in chunked(thumbnail, 10)], dtype=np.uint8)
    strip = ndi.gaussian_filter1d(strip, sigma=1, axis=0)
    strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1), order=1)
    strip = strip / 255.

    return strip


def _saturation_key(rgb):
    # return 1
    mn, mx = min(rgb)/255., max(rgb)/255.
    lum = (mx+mn)/2
    if mx < 0.01 or mn > 0.99:
        return 0
    else:
        return (mx-mn) * 0.8 + 0.2
        # return (mx - mn) / (1 - abs(2 * lum - 1)) * lum * 0.8 + 0.2


def _get_dominant_color(image):
    img = Image.fromarray(image, 'RGB')
    paletted = img.convert('P', palette=Image.ADAPTIVE, colors=8)
    palette = list(chunked(paletted.getpalette(), 3))
    # print("palette: ", palette)

    mx_col = max(paletted.getcolors(), key=lambda pair: pair[0] * _saturation_key(palette[pair[1]]))
    # print("mx_col: ", mx_col)

    return palette[mx_col[1]]

# if __name__ == '__main__':
#     pass

