from skimage import exposure, filters, io
from skimage.util import img_as_ubyte, img_as_float
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
import numpy as np
from sortedcontainers import SortedKeyList
from datetime import datetime
import imageio.v3 as iio

CANVAS_HEIGHT = 1000
STRIP_BLUR_RADIUS = CANVAS_HEIGHT / 20


def _generate_strip(image: np.array) -> np.array:
    strip = np.median(image, axis=1)
    if image.shape[0] != CANVAS_HEIGHT:
        strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1))
    strip = ndi.gaussian_filter1d(strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    return strip


class Media:
    def __init__(self, payload):
        media_id = payload['media_id']
        caption = payload['caption']
        media_type = payload['media_type']
        permalink = payload['permalink']
        username = payload['username']
        timestamp = datetime.strptime(payload['timestamp'], "%Y-%m-%dT%H:%M:%S%z").timestamp()
        media_url = payload['media_url']
        strip = None
        if media_type in ["IMAGE", "CAROUSEL_ALBUM"]:
            # image = iio.imread(media_url, index=None)
            strip = _generate_strip(iio.imread(media_url, index=None))

# if __name__ == '__main__':
    pass

