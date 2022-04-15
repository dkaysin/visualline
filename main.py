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

# Generate sample dataset
def dataset():
    im_coll = io.ImageCollection('./dataset/*.jpg')
    # print("Length of dataset:", len(im_coll))

    base_ts = 1331856000
    # ts_coll = [datetime.datetime.fromtimestamp(base_ts + t*100000) for t in range(len(im_coll))]
    ts_coll = SortedList([base_ts + t * random.uniform(1, 1.3) * 100000 for t in range(len(im_coll))])
    return im_coll, ts_coll


def strip_vert(im):
    # im = exposure.rescale_intensity(im)
    STRIP_BLUR_RADIUS = HEIGHT/20
    strip = np.median(im, axis=1)
    if im.shape[0] != HEIGHT:
        strip = ndi.zoom(strip, (HEIGHT / strip.shape[0], 1))
    strip = ndi.gaussian_filter1d(strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    return strip
    # strip = filters.gaussian(strip, HEIGHT / 20, channel_axis=1)
    # strip_img = transform.resize(np.array([strip]), (1, HEIGHT), anti_aliasing=True)
    # return strip_img[0]


def strips_bg(strips):
    BG_GAMMA_FACTOR = 0.25
    BG_BLUR_RADIUS = HEIGHT/8
    line = np.median(strips, axis=0) * BG_GAMMA_FACTOR
    line = ndi.gaussian_filter1d(line, sigma=BG_BLUR_RADIUS, axis=0)
    return line


def test():
    im_coll, ts_coll = dataset()
    strips = [strip_vert(img_as_float(im)) for im in im_coll]

    # Draw gradient
    canvas = np.full((WIDTH, HEIGHT, 3), strips_bg(strips), dtype=float)
    canvas = insert_gradient(canvas, strips, ts_coll)

    # Draw glowing strips
    layer = np.full((WIDTH, HEIGHT, 3), 0, dtype=float)
    insert_strips(layer, strips, ts_coll)
    layer = filters.gaussian(layer, 10, channel_axis=2)
    insert_strips(layer, strips, ts_coll)
    layer = filters.gaussian(layer, 3, channel_axis=2)
    insert_strips(layer, strips, ts_coll)

    # Blend (screen mode)
    canvas = 1 - (1-canvas) * (1-layer)

    # Post-processing
    canvas = exposure.rescale_intensity(canvas, (0., 1))
    canvas = rgb2hsv(canvas)
    PP_SATURATION_GAIN = 1.3
    canvas[:, :, 1] = 1 - (1-canvas[:, :, 1]) ** PP_SATURATION_GAIN
    canvas = hsv2rgb(canvas)

    render(canvas, ts_coll)


def insert_strips(canvas, strips, timestamps):
    for (s, t) in zip(strips, timestamps):
        hi = max(timestamps)
        lo = min(timestamps)
        n = int((t-lo)/(hi-lo) * (WIDTH-1))
        canvas[n] = s
    return canvas


def insert_gradient(canvas, strips, timestamps):
    hi = max(timestamps)
    lo = min(timestamps)
    for n, col in enumerate(canvas):
        ts_interp = ((n / WIDTH) * (hi-lo) + lo)
        index_floor = timestamps.bisect_left(ts_interp + 1) - 1
        index_ceil = timestamps.bisect_right(ts_interp - 1)
        ts_floor = timestamps[index_floor]
        ts_ceil = timestamps[index_ceil]
        if ts_ceil - ts_floor != 0:
            w = (ts_interp - ts_floor) / (ts_ceil - ts_floor)
        else:
            w = 1
        GRADIENT_DEGREE_FLOOR = 2
        GRADIENT_DEGREE_CEIL = 4
        weight_floor = (1-w) ** GRADIENT_DEGREE_FLOOR
        weight_ceil = w ** GRADIENT_DEGREE_CEIL
        canvas[n] = strips[index_floor] * weight_floor \
            + strips[index_ceil] * weight_ceil \
            + canvas[n] * (1 - weight_floor - weight_ceil)
        # canvas[n] = strips[index_floor] * weight_floor \
        #     + canvas[n] * (1 - weight_floor)
    return canvas


def render(strips, ts_coll):
    strips = np.transpose(strips, (1, 0, 2))
    io.imsave('./out.jpg', img_as_ubyte(strips))


if __name__ == '__main__':
    test()
    # sl = SortedList([8, 20, 40, 60, 90])
    # print(sl.bisect_right(9))

