from skimage import exposure, filters, io
from skimage.util import img_as_ubyte
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
import numpy as np
from sortedcontainers import SortedKeyList

from Media import Media

CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 1000

BG_GAMMA_FACTOR = 0.25
BG_BLUR_RADIUS = CANVAS_HEIGHT / 8

GRADIENT_DEGREE_FLOOR = 2
GRADIENT_DEGREE_CEIL = 4

PP_SATURATION_GAIN = 1.3


def _post_process(canvas: np.array) -> np.array:
    canvas = exposure.rescale_intensity(canvas, (0., 1))
    canvas = rgb2hsv(canvas)
    canvas[:, :, 1] = 1 - (1 - canvas[:, :, 1]) ** PP_SATURATION_GAIN
    canvas = hsv2rgb(canvas)
    return canvas


def _strips_bg(media_list: SortedKeyList[Media]) -> np.array:
    strips = [media.strip for media in media_list]
    line = np.median(strips, axis=0) * BG_GAMMA_FACTOR
    line = ndi.gaussian_filter1d(line, sigma=BG_BLUR_RADIUS, axis=0)
    return line


def _insert_strips(canvas: np.array, media_list: SortedKeyList[Media]) -> np.array:
    # for (s, t) in zip(strips, timestamps):
    #     hi = max(timestamps)
    #     lo = min(timestamps)
    #     n = int((t-lo) / (hi-lo) * (CANVAS_WIDTH - 1))
    #     canvas[n] = s
    # return canvas

    hi = max([m.timestamp for m in media_list])
    lo = min([m.timestamp for m in media_list])
    for media in media_list:
        if (media.strip is None) or (media.timestamp is None):
            continue
        t = media.timestamp
        n = int((t-lo) / (hi-lo) * (CANVAS_WIDTH - 1))
        canvas[n] = media.strip


def _insert_gradient(canvas: np.array, media_list: SortedKeyList[Media]) -> np.array:
    # hi = max(timestamps)
    # lo = min(timestamps)
    # for n, col in enumerate(canvas):
    #     ts_interp = ((n / CANVAS_WIDTH) * (hi - lo) + lo)
    #     index_floor = timestamps.bisect_left(ts_interp + 1) - 1
    #     index_ceil = timestamps.bisect_right(ts_interp - 1)
    #     ts_floor = timestamps[index_floor]
    #     ts_ceil = timestamps[index_ceil]
    #     if ts_ceil - ts_floor != 0:
    #         w = (ts_interp - ts_floor) / (ts_ceil - ts_floor)
    #     else:
    #         w = 1
    #     weight_floor = (1-w) ** GRADIENT_DEGREE_FLOOR
    #     weight_ceil = w ** GRADIENT_DEGREE_CEIL
    #     canvas[n] = strips[index_floor] * weight_floor \
    #       + strips[index_ceil] * weight_ceil \
    #       + canvas[n] * (1 - weight_floor - weight_ceil)
    #     canvas[n] = strips[index_floor] * weight_floor \
    #       + canvas[n] * (1 - weight_floor)

    hi = max([m.timestamp for m in media_list])
    lo = min([m.timestamp for m in media_list])
    for n, col in enumerate(canvas):
        ts_interp = ((n / CANVAS_WIDTH) * (hi - lo) + lo)
        index_floor = media_list.bisect_key_left(ts_interp + 1).timestamp - 1
        index_ceil = media_list.bisect_key_left(ts_interp - 1).timestamp
        ts_floor = media_list[index_floor].timestamp
        ts_ceil = media_list[index_ceil].timestamp
        if ts_ceil - ts_floor != 0:
            w = (ts_interp - ts_floor) / (ts_ceil - ts_floor)
        else:
            w = 1
        weight_floor = (1-w) ** GRADIENT_DEGREE_FLOOR
        weight_ceil = w ** GRADIENT_DEGREE_CEIL
        canvas[n] = media_list[index_floor].strip * weight_floor \
            + media_list[index_ceil].strip * weight_ceil \
            + canvas[n] * (1 - weight_floor - weight_ceil)

    return canvas


# def get_strips(images) -> SortedKeyList[Media]:
#     return SortedKeyList(
#         [Media(im) for im in images],
#         key=(lambda m: m.timestamp)
#     )


def draw(media_list: SortedKeyList[Media]) -> np.array:
    if len(media_list) < 2:
        raise ValueError('Not enough images')
    # if len(strips) != len(timestamps):
    #     raise ValueError('Images and timestamp list lengths do not match')

    # draw gradient
    canvas = np.full((CANVAS_WIDTH, CANVAS_HEIGHT, 3), 0, dtype=float)
    canvas = _insert_gradient(canvas, media_list)
    # draw glowing strips
    layer = np.full((CANVAS_WIDTH, CANVAS_HEIGHT, 3), 0, dtype=float)
    _insert_strips(layer, media_list)
    layer = filters.gaussian(layer, 10, channel_axis=2)
    _insert_strips(layer, media_list)
    layer = filters.gaussian(layer, 3, channel_axis=2)
    _insert_strips(layer, media_list)
    # blend (screen mode)
    canvas = 1 - (1-canvas) * (1-layer)
    # post-processing
    canvas = _post_process(canvas)
    # swap rows and columns
    canvas = np.transpose(canvas, (1, 0, 2))
    # Convert from float[-1.,1.] to uint8[0,255]
    canvas = img_as_ubyte(canvas)
    return canvas


def save_on_disk(canvas: np.array):
    io.imsave('./out.jpg', canvas)