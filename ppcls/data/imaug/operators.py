"""
# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import six
import math
import random
import cv2
import numpy as np
import time

from .autoaugment import ImageNetPolicy


class OperatorParamError(ValueError):
    """ OperatorParamError
    """
    pass


class DecodeImage(object):
    """ decode image """

    def __init__(self, to_rgb=True, to_np=False, channel_first=False):
        self.to_rgb = to_rgb
        self.to_np = to_np  # to numpy
        self.channel_first = channel_first  # only enabled when to_np is True

    def __call__(self, img):
        tic = time.time()
        if six.PY2:
            assert type(img) is str and len(
                img) > 0, "invalid input 'img' in DecodeImage"
        else:
            assert type(img) is bytes and len(
                img) > 0, "invalid input 'img' in DecodeImage"
        data = np.frombuffer(img, dtype='uint8')
        img = cv2.imdecode(data, 1)
        if self.to_rgb:
            assert img.shape[2] == 3, 'invalid shape of image[%s]' % (
                img.shape)
            img = img[:, :, ::-1]

        if self.channel_first:
            img = img.transpose((2, 0, 1))
        print("Decode image: {} s".format(time.time() - tic))
        return img


class ResizeImage(object):
    """ resize image """

    def __init__(self, size=None, resize_short=None, interpolation=-1):
        self.interpolation = interpolation if interpolation >= 0 else None
        if resize_short is not None and resize_short > 0:
            self.resize_short = resize_short
            self.w = None
            self.h = None
        elif size is not None:
            self.resize_short = None
            self.w = size if type(size) is int else size[0]
            self.h = size if type(size) is int else size[1]
        else:
            raise OperatorParamError("invalid params for ReisizeImage for '\
                'both 'size' and 'resize_short' are None")

    def __call__(self, img):
        tic = time.time()
        img_h, img_w = img.shape[:2]
        if self.resize_short is not None:
            percent = float(self.resize_short) / min(img_w, img_h)
            w = int(round(img_w * percent))
            h = int(round(img_h * percent))
        else:
            w = self.w
            h = self.h
        if self.interpolation is None:
            print("Resize image: {} s".format(time.time() - tic))
            return cv2.resize(img, (w, h))
        else:
            print("Resize image: {} s".format(time.time() - tic))
            return cv2.resize(img, (w, h), interpolation=self.interpolation)


class CropImage(object):
    """ crop image """

    def __init__(self, size):
        if type(size) is int:
            self.size = (size, size)
        else:
            self.size = size  # (h, w)

    def __call__(self, img):
        tic = time.time()
        w, h = self.size
        img_h, img_w = img.shape[:2]
        w_start = (img_w - w) // 2
        h_start = (img_h - h) // 2

        w_end = w_start + w
        h_end = h_start + h

        print("Crop image: {} s".format(time.time() - tic))
        return img[h_start:h_end, w_start:w_end, :]


class RandCropImage(object):
    """ random crop image """

    def __init__(self, size, scale=None, ratio=None, interpolation=-1):

        self.interpolation = interpolation if interpolation >= 0 else None
        if type(size) is int:
            self.size = (size, size)  # (h, w)
        else:
            self.size = size

        self.scale = [0.08, 1.0] if scale is None else scale
        self.ratio = [3. / 4., 4. / 3.] if ratio is None else ratio

    def __call__(self, img):
        size = self.size
        scale = self.scale
        ratio = self.ratio

        aspect_ratio = math.sqrt(random.uniform(*ratio))
        w = 1. * aspect_ratio
        h = 1. / aspect_ratio

        img_h, img_w = img.shape[:2]

        bound = min((float(img_w) / img_h) / (w**2),
                    (float(img_h) / img_w) / (h**2))
        scale_max = min(scale[1], bound)
        scale_min = min(scale[0], bound)

        target_area = img_w * img_h * random.uniform(scale_min, scale_max)
        target_size = math.sqrt(target_area)
        w = int(target_size * w)
        h = int(target_size * h)

        i = random.randint(0, img_w - w)
        j = random.randint(0, img_h - h)

        img = img[j:j + h, i:i + w, :]
        if self.interpolation is None:
            return cv2.resize(img, size)
        else:
            return cv2.resize(img, size, interpolation=self.interpolation)


class RandFlipImage(object):
    """ random flip image
        flip_code:
            1: Flipped Horizontally
            0: Flipped Vertically
            -1: Flipped Horizontally & Vertically
    """

    def __init__(self, flip_code=1):
        assert flip_code in [-1, 0, 1
                             ], "flip_code should be a value in [-1, 0, 1]"
        self.flip_code = flip_code

    def __call__(self, img):
        if random.randint(0, 1) == 1:
            return cv2.flip(img, self.flip_code)
        else:
            return img


class AutoAugment(object):
    def __init__(self):
        self.policy = ImageNetPolicy()

    def __call__(self, img):
        from PIL import Image
        img = np.ascontiguousarray(img)
        img = Image.fromarray(img)
        img = self.policy(img)
        img = np.asarray(img)


class NormalizeImage(object):
    """ normalize image such as substract mean, divide std
    """

    def __init__(self, scale=None, mean=None, std=None, order='chw'):
        if isinstance(scale, str):
            scale = eval(scale)
        self.scale = np.float32(scale if scale is not None else 1.0 / 255.0)
        mean = mean if mean is not None else [0.485, 0.456, 0.406]
        std = std if std is not None else [0.229, 0.224, 0.225]

        shape = (3, 1, 1) if order == 'chw' else (1, 1, 3)
        self.mean = np.array(mean).reshape(shape).astype('float32')
        self.std = np.array(std).reshape(shape).astype('float32')

    def __call__(self, img):
        from PIL import Image
        if isinstance(img, Image.Image):
            img = np.array(img)

        assert isinstance(img,
                          np.ndarray), "invalid input 'img' in NormalizeImage"
        return (img.astype('float32') * self.scale - self.mean) / self.std


class ToCHWImage(object):
    """ convert hwc image to chw image
    """

    def __init__(self):
        pass

    def __call__(self, img):
        from PIL import Image
        if isinstance(img, Image.Image):
            img = np.array(img)

        return img.transpose((2, 0, 1))
