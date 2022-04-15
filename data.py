from sortedcontainers import SortedList
import random
from skimage import exposure, filters, io


def get_data(account_name):
    return sample_dataset()

def sample_dataset():
    _images = io.ImageCollection('./dataset/*.jpg')
    print("Length of dataset:", len(_images))
    base_ts = 1331856000
    _timestamps = SortedList([base_ts + t * random.uniform(1, 1.3) * 100000 for t in range(len(_images))])
    return _images, _timestamps
