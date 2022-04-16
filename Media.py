from skimage import exposure, filters, io
from skimage.util import img_as_ubyte, img_as_float
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
import numpy as np
from sortedcontainers import SortedKeyList
from datetime import datetime
import imageio.v3 as iio
import math

CANVAS_HEIGHT = 1000
STRIP_BLUR_RADIUS = CANVAS_HEIGHT / 20


def _generate_strip(image: np.array) -> np.array:
    strip = np.median(image, axis=1)
    if image.shape[0] != CANVAS_HEIGHT:
        strip = ndi.zoom(strip, (CANVAS_HEIGHT / strip.shape[0], 1))
    strip = ndi.gaussian_filter1d(strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    return strip


def parse_media(payload):
    print(payload)
    media_type = payload['media_type']
    if media_type in ["IMAGE", "CAROUSEL_ALBUM"]:
        return Media(payload)
    else:
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
        print("Processing image: ", self.media_id)
        image = img_as_float(iio.imread(self.media_url))
        self.strip = _generate_strip(image)

# if __name__ == '__main__':
    pass

