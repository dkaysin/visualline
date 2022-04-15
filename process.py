from skimage import exposure, filters, io
from skimage.util import img_as_ubyte, img_as_float
from skimage.color import rgb2hsv, hsv2rgb
from scipy import ndimage as ndi
import numpy as np

CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 1000

STRIP_BLUR_RADIUS = CANVAS_HEIGHT / 20

BG_GAMMA_FACTOR = 0.25
BG_BLUR_RADIUS = CANVAS_HEIGHT / 8

GRADIENT_DEGREE_FLOOR = 2
GRADIENT_DEGREE_CEIL = 4

PP_SATURATION_GAIN = 1.3


def _strip_vert(_image):

    _strip = np.median(_image, axis=1)
    if _image.shape[0] != CANVAS_HEIGHT:
        _strip = ndi.zoom(_strip, (CANVAS_HEIGHT / _strip.shape[0], 1))
    _strip = ndi.gaussian_filter1d(_strip, sigma=STRIP_BLUR_RADIUS, axis=0)
    return _strip


def _strips_bg(_strips):
    _line = np.median(_strips, axis=0) * BG_GAMMA_FACTOR
    _line = ndi.gaussian_filter1d(_line, sigma=BG_BLUR_RADIUS, axis=0)
    return _line


def _post_process(_canvas):
    _canvas = exposure.rescale_intensity(_canvas, (0., 1))
    _canvas = rgb2hsv(_canvas)
    _canvas[:, :, 1] = 1 - (1 - _canvas[:, :, 1]) ** PP_SATURATION_GAIN
    _canvas = hsv2rgb(_canvas)
    return _canvas


def _insert_strips(_canvas, _strips, _timestamps):
    for (s, t) in zip(_strips, _timestamps):
        hi = max(_timestamps)
        lo = min(_timestamps)
        n = int((t-lo) / (hi-lo) * (CANVAS_WIDTH - 1))
        _canvas[n] = s
    return _canvas


def _insert_gradient(_canvas, _strips, _timestamps):
    hi = max(_timestamps)
    lo = min(_timestamps)
    for n, col in enumerate(_canvas):
        ts_interp = ((n / CANVAS_WIDTH) * (hi - lo) + lo)
        index_floor = _timestamps.bisect_left(ts_interp + 1) - 1
        index_ceil = _timestamps.bisect_right(ts_interp - 1)
        ts_floor = _timestamps[index_floor]
        ts_ceil = _timestamps[index_ceil]
        if ts_ceil - ts_floor != 0:
            w = (ts_interp - ts_floor) / (ts_ceil - ts_floor)
        else:
            w = 1
        weight_floor = (1-w) ** GRADIENT_DEGREE_FLOOR
        weight_ceil = w ** GRADIENT_DEGREE_CEIL
        _canvas[n] = _strips[index_floor] * weight_floor \
            + _strips[index_ceil] * weight_ceil \
            + _canvas[n] * (1 - weight_floor - weight_ceil)
        # _canvas[n] = strips[index_floor] * weight_floor \
        #     + _canvas[n] * (1 - weight_floor)
    return _canvas


def get_strips(_images):
    return [_strip_vert(img_as_float(im)) for im in _images]


def draw(_strips, _timestamps):
    if len(_strips) < 2:
        raise ValueError('Not enough images')
    if len(_strips) != len(_timestamps):
        raise ValueError('Images and timestamp list lengths do not match')
    # draw gradient
    _canvas = np.full((CANVAS_WIDTH, CANVAS_HEIGHT, 3), 0, dtype=float)
    _canvas = _insert_gradient(_canvas, _strips, _timestamps)
    # draw glowing strips
    _layer = np.full((CANVAS_WIDTH, CANVAS_HEIGHT, 3), 0, dtype=float)
    _insert_strips(_layer, _strips, _timestamps)
    _layer = filters.gaussian(_layer, 10, channel_axis=2)
    _insert_strips(_layer, _strips, _timestamps)
    _layer = filters.gaussian(_layer, 3, channel_axis=2)
    _insert_strips(_layer, _strips, _timestamps)
    # blend (screen mode)
    _canvas = 1 - (1-_canvas) * (1-_layer)
    # post-processing
    _canvas = _post_process(_canvas)
    # swap rows and columns
    _canvas = np.transpose(_canvas, (1, 0, 2))
    # Convert from float[-1.,1.] to uint8[0,255]
    _canvas = img_as_ubyte(_canvas)
    return _canvas


def render(im):
    io.imsave('./out.jpg', im)


# if __name__ == '__main__':
    # images, timestamps = dataset()
    # strips = get_strips(images)
    # canvas = draw(strips, timestamps)
    # render(canvas)

