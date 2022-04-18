from skimage.util import img_as_ubyte, img_as_float
from scipy import ndimage as ndi
import numpy as np
from datetime import datetime
import imageio.v3 as iio
import asyncio as aio
import time

CANVAS_HEIGHT = 1000
STRIP_BLUR_RADIUS = CANVAS_HEIGHT / 20


async def parse_media(sem, client, payload):
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
                    image = img_as_float(iio.imread(img_bytes))
                except Exception:  # TODO more specific exception must be used
                    # await aio.sleep(0.1 * 2**tries)
                    await aio.sleep(0.1)
            if image is not None:
                media.strip = generate_strip(image)
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


def generate_strip(image: np.array) -> np.array:
    start_time = time.time()
    subsampling = 5
    if image is None:
        raise ValueError("Image provided to generate_strip is None")
    strip = np.median(image[::subsampling, ::subsampling, ::], axis=1)
    # strip = ndi.zoom(strip, (2/strip.shape[0], 1))
    # strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1))
    if image.shape[0] != CANVAS_HEIGHT:
        strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1))
    strip = ndi.gaussian_filter1d(strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    # print("<generate_strip> execution time: --- %s seconds ---" % (time.time() - start_time))
    return strip


# if __name__ == '__main__':
#     pass

