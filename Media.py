import numpy as np
from datetime import datetime
import asyncio as aio
from more_itertools import chunked
import io
import os
import time
from PIL import Image, ImageFilter
import psycopg2

DEBUG_MODE = os.environ.get('DEBUG_MODE') == "True"

THUMB_WIDTH = 100
THUMB_HEIGHT = 50


async def parse_media(db_cur, sem, client, CANVAS_HEIGHT: int, payload):
    media = Media(payload)
    image = None

    db_cur.execute("""SELECT (media_strip_thumb) FROM media 
        WHERE media_id=%s;
    """, [media.media_id])
    strip_cached = db_cur.fetchone()
    if strip_cached is not None:
        media.strip_thumb = Image.open(io.BytesIO(strip_cached[0]))

    if media.strip_thumb is None:
        if media.media_type in ["IMAGE", "CAROUSEL_ALBUM"]:
            url = payload.get('media_url')
            tries = 0
            async with sem:
                while (image is None) and (tries <= 5):
                    tries += 1
                    # print(f"Fetching media {media.media_id} from {media.media_url}. Try: {tries}")
                    try:
                        response = await client.get(url)
                        img_bytes = io.BytesIO(response.content)
                        image = Image.open(img_bytes).resize((THUMB_WIDTH, THUMB_HEIGHT), resample=Image.NEAREST)
                    except Exception as err:  # TODO more specific exception must be used
                        print(err)
                        # await aio.sleep(0.1 * 2**tries)
                        await aio.sleep(0.1)

            if image is not None:
                media.strip_thumb = generate_strip_thumb(image)
                with io.BytesIO() as output:
                    media.strip_thumb.save(output, format="JPEG")
                    db_cur.execute("""INSERT INTO media (media_id, media_strip_thumb)
                        VALUES (%s, %s)
                        ON CONFLICT (media_id) DO UPDATE SET media_strip_thumb = %s;
                   """, [media.media_id, psycopg2.Binary(output.getvalue()), psycopg2.Binary(output.getvalue())])

    if media.strip_thumb is None:
        return None
    else:
        media.strip = generate_strip(media.strip_thumb, CANVAS_HEIGHT)
        return media


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
        self.strip_thumb = None
        self.strip = None

    def __str__(self):
        return f"id: {self.media_id}, Timestamp: {self.timestamp}, strip_position: {self.strip_position}, strip: {self.strip}"


def generate_strip(stripe: Image.Image, CANVAS_HEIGHT: int) -> np.array:
    res = stripe.resize((CANVAS_HEIGHT, 1), resample=Image.BILINEAR)
    return np.array(res)[0]/255


def generate_strip_thumb(image: Image.Image) -> Image.Image:
    if image is None:
        raise ValueError("Image provided to generate_strip is None")

    # subsampling = int(image.shape[1] / 200)
    # image = img_as_float(image)
    # strip = np.median(image[::subsampling, ::subsampling, ::], axis=1)
    # if strip.shape[0] != CANVAS_HEIGHT:
    #     strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1), order=1)
    # strip_blur_radius = CANVAS_HEIGHT / 20
    # strip = ndi.gaussian_filter1d(strip, sigma=strip_blur_radius, axis=0)

    bands = 10
    thumb_height = image.size[0]
    thumb_width = image.size[1]
    stride = thumb_width//bands
    arr = []
    for n in range(0, thumb_width, stride):
        strip = image.crop((0, n, thumb_height, n+stride))
        dom_color = _get_dominant_color(strip)
        if dom_color is not None:
            arr.append(dom_color)

    # strip = np.array([_get_dominant_color(np.array(chunk)) for chunk in chunked(image, 5)], dtype=np.uint8)
    # strip = ndi.gaussian_filter1d(strip, sigma=1, axis=0)
    # strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1), order=1)
    # # strip = ndi.gaussian_filter1d(strip, sigma=CANVAS_HEIGHT / 20, axis=0)
    # strip = strip / 255.

    if len(arr) == 0:
        return None
    else:
        return Image.fromarray(np.array([arr], dtype=np.uint8), mode="RGB").filter(ImageFilter.BoxBlur(1))


def _saturation_key(rgb):
    # return 1
    mn, mx = min(rgb)/255., max(rgb)/255.
    lum = (mx+mn)/2
    if mx < 0.01 or mn > 0.99:
        sat = 0.2
    else:
        sat = mx - mn
        # return (mx - mn) / (1 - abs(2 * lum - 1)) * lum * 0.8 + 0.2
    return sat * 0.8 + 0.2


def _get_dominant_color(image: Image.Image):
    # start_time = time.time()
    paletted = image.convert('P', palette=Image.ADAPTIVE, colors=8)
    palette = list(chunked(paletted.getpalette(), 3))
    dominant_color = max(paletted.getcolors(), key=lambda pair: pair[0] * _saturation_key(palette[pair[1]]))
    # print("_get_dominant_color time: --- %s seconds ---" % (time.time() - start_time))
    res = palette[dominant_color[1]]
    is_white = res[0] == 255 and res[1] == 255 and res[2] == 255
    is_black = res[0] == 0 and res[1] == 0 and res[2] == 0
    if is_white or is_black:
        return None
    else:
        return res


# if __name__ == '__main__':
#     pass

