from skimage import exposure, filters, io
from skimage.util import img_as_ubyte, img_as_float
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
from sortedcontainers import SortedList
import random
import numpy as np
import datetime

WIDTH = 1000
HEIGHT = 1000


def dataset():
    _images = io.ImageCollection('./dataset/*.jpg')
    print("Length of dataset:", len(_images))
    base_ts = 1331856000
    _timestamps = SortedList([base_ts + t * random.uniform(1, 1.3) * 100000 for t in range(len(_images))])
    return _images, _timestamps


def strip_vert(_image):
    STRIP_BLUR_RADIUS = HEIGHT/20
    _strip = np.median(_image, axis=1)
    if _image.shape[0] != HEIGHT:
        _strip = ndi.zoom(_strip, (HEIGHT / _strip.shape[0], 1))
    _strip = ndi.gaussian_filter1d(_strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    return _strip
    # strip = filters.gaussian(strip, HEIGHT / 20, channel_axis=1)
    # strip_img = transform.resize(np.array([strip]), (1, HEIGHT), anti_aliasing=True)
    # return strip_img[0]


def strips_bg(_strips):
    BG_GAMMA_FACTOR = 0.25
    BG_BLUR_RADIUS = HEIGHT/8
    _line = np.median(_strips, axis=0) * BG_GAMMA_FACTOR
    _line = ndi.gaussian_filter1d(_line, sigma=BG_BLUR_RADIUS, axis=0)
    return _line


def get_strips(_images):
    return [strip_vert(img_as_float(im)) for im in _images]

def draw(_strips, _timestamps):
    if len(_strips) < 2:
        raise ValueError('Not enough images')
    if len(_strips) != len(_timestamps):
        raise ValueError('Images and timestamp list lengths do not match')
    # Draw gradient
    _canvas = np.full((WIDTH, HEIGHT, 3), 0, dtype=float)
    _canvas = insert_gradient(_canvas, _strips, _timestamps)
    # Draw glowing strips
    _layer = np.full((WIDTH, HEIGHT, 3), 0, dtype=float)
    insert_strips(_layer, _strips, _timestamps)
    _layer = filters.gaussian(_layer, 10, channel_axis=2)
    insert_strips(_layer, _strips, _timestamps)
    _layer = filters.gaussian(_layer, 3, channel_axis=2)
    insert_strips(_layer, _strips, _timestamps)
    # Blend (screen mode)
    _canvas = 1 - (1-_canvas) * (1-_layer)
    # Post-processing
    _canvas = post_process(_canvas)
    return _canvas


def post_process(_canvas):
    _canvas = exposure.rescale_intensity(_canvas, (0., 1))
    _canvas = rgb2hsv(_canvas)
    PP_SATURATION_GAIN = 1.3
    _canvas[:, :, 1] = 1 - (1 - _canvas[:, :, 1]) ** PP_SATURATION_GAIN
    _canvas = hsv2rgb(_canvas)
    return _canvas


def insert_strips(_canvas, _strips, _timestamps):
    for (s, t) in zip(_strips, _timestamps):
        hi = max(_timestamps)
        lo = min(_timestamps)
        n = int((t-lo)/(hi-lo) * (WIDTH-1))
        _canvas[n] = s
    return _canvas


def insert_gradient(_canvas, _strips, _timestamps):
    hi = max(_timestamps)
    lo = min(_timestamps)
    for n, col in enumerate(_canvas):
        ts_interp = ((n / WIDTH) * (hi-lo) + lo)
        index_floor = _timestamps.bisect_left(ts_interp + 1) - 1
        index_ceil = _timestamps.bisect_right(ts_interp - 1)
        ts_floor = _timestamps[index_floor]
        ts_ceil = _timestamps[index_ceil]
        if ts_ceil - ts_floor != 0:
            w = (ts_interp - ts_floor) / (ts_ceil - ts_floor)
        else:
            w = 1
        GRADIENT_DEGREE_FLOOR = 2
        GRADIENT_DEGREE_CEIL = 4
        weight_floor = (1-w) ** GRADIENT_DEGREE_FLOOR
        weight_ceil = w ** GRADIENT_DEGREE_CEIL
        _canvas[n] = _strips[index_floor] * weight_floor \
            + _strips[index_ceil] * weight_ceil \
            + _canvas[n] * (1 - weight_floor - weight_ceil)
        # _canvas[n] = strips[index_floor] * weight_floor \
        #     + _canvas[n] * (1 - weight_floor)
    return _canvas


def render(im):
    im = np.transpose(im, (1, 0, 2))
    io.imsave('./out.jpg', img_as_ubyte(im))


if __name__ == '__main__':
    images, timestamps = dataset()
    strips = get_strips(images)
    canvas = draw(strips, timestamps)
    render(canvas)

