from skimage import exposure, filters, io
from skimage.util import img_as_ubyte
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
import numpy as np
from sortedcontainers import SortedKeyList

from Media import Media

BG_GAMMA_FACTOR = 0.25

GRADIENT_DEGREE_FLOOR = 0.75
GRADIENT_DEGREE_CEIL = 4

PP_SATURATION_GAIN = 1.3


def _post_process(canvas: np.array) -> np.array:
    canvas = exposure.rescale_intensity(canvas, (0., 1.))
    canvas = rgb2hsv(canvas)
    canvas[:, :, 1] = 1 - (1 - canvas[:, :, 1]) ** PP_SATURATION_GAIN
    canvas = hsv2rgb(canvas)
    return canvas


def _strips_bg(media_list: SortedKeyList[Media]) -> np.array:
    strips = [media.strip for media in media_list]
    line = np.median(strips, axis=0) * BG_GAMMA_FACTOR
    blur_radius = line.shape[0] / 8  # TODO test this
    line = ndi.gaussian_filter1d(line, sigma=blur_radius, axis=0)
    return line


def _insert_strips(canvas: np.array, media_list: SortedKeyList[Media]) -> np.array:
    positions = [m.strip_position for m in media_list]
    lo, hi = min(positions), max(positions)
    for media in media_list:
        if (media.strip is None) or (media.strip_position is None):
            continue
        t = media.strip_position
        n = int((t-lo) / (hi-lo) * (canvas.shape[0] - 1))
        canvas[n] = media.strip


def _insert_gradient(canvas: np.array, media_list: SortedKeyList[Media], style: int):
    positions = [m.strip_position for m in media_list]
    lo, hi = min(positions), max(positions)
    for n, col in enumerate(canvas):
        ts_interp = n / (canvas.shape[0] - 1) * (hi - lo) + lo
        index_floor = media_list.bisect_key_left(ts_interp + 0.001) - 1
        index_ceil = media_list.bisect_key_left(ts_interp - 0.001)
        ts_floor = media_list[index_floor].strip_position
        ts_ceil = media_list[index_ceil].strip_position

        if style == 1:
            canvas[n] = media_list[index_floor].strip * 0.8

        else:
            if ts_ceil - ts_floor != 0:
                w = (ts_interp - ts_floor) / (ts_ceil - ts_floor)
            else:
                w = 1
            weight_floor = (1 - w) ** GRADIENT_DEGREE_FLOOR
            weight_ceil = w ** GRADIENT_DEGREE_CEIL
            canvas[n] = media_list[index_floor].strip * weight_floor \
                + media_list[index_ceil].strip * weight_ceil \
                + canvas[n] * (1 - weight_floor - weight_ceil)


def draw(media_list: SortedKeyList[Media], canvas_width: int, canvas_height: int, style: int) -> np.array:
    if len(media_list) < 2:
        raise ValueError('Not enough images')

    # draw gradient
    canvas = np.full((canvas_width, canvas_height, 3), 0, dtype=float)
    _insert_gradient(canvas, media_list, style)
    layer = np.full((canvas_width, canvas_height, 3), 0, dtype=float)
    if style == 1:
        _insert_strips(layer, media_list)
        layer = filters.gaussian(layer, 10, channel_axis=2, mode="constant")
        layer *= 1.5
        _insert_strips(layer, media_list)
        layer = filters.gaussian(layer, 3, channel_axis=2, mode="constant")
        layer *= 1.5
        _insert_strips(layer, media_list)
        layer *= 0.8
    else:
        _insert_strips(layer, media_list)
        layer = filters.gaussian(layer, 10, channel_axis=2, mode="constant")
        _insert_strips(layer, media_list)
        layer = filters.gaussian(layer, 3, channel_axis=2, mode="constant")
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


def save_on_disk(account_id: str, canvas: np.array):
    io.imsave(f"./{account_id}.jpg", canvas)