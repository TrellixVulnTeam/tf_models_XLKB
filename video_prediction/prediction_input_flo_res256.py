# Copyright 2016 The TensorFlow Authors All Rights Reserved.
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
# ==============================================================================

"""Code for building the input for the prediction model."""

import os

import numpy as np
import tensorflow as tf

from tensorflow.python.platform import flags
from tensorflow.python.platform import gfile

DATA_DIR = '/home/wangyang59/Data/ILSVRC2016_tf_flo'
#DATA_DIR = '/home/wangyang59/Data/ILSVRC2016_tf_stab/train'
FLAGS = flags.FLAGS

# Original image dimensions
ORIGINAL_WIDTH = 256
ORIGINAL_HEIGHT = 256
COLOR_CHAN = 3

# Default image dimensions.
IMG_WIDTH = 256
IMG_HEIGHT = 256

# Dimension of the state and action.
STATE_DIM = 5


def build_tfrecord_input(training=True, blacklist=[]):
  """Create input tfrecord tensors.

  Args:
    training: training or validation data.
  Returns:
    list of tensors corresponding to images, actions, and states. The images
    tensor is 5D, batch x time x height x width x channels. The state and
    action tensors are 3D, batch x time x dimension.
  Raises:
    RuntimeError: if no files found.
  """
  filenames = gfile.Glob(os.path.join(FLAGS.data_dir, '*'))
  filenames = filter(lambda x: x.split("/")[-1] not in blacklist, filenames)
  if not filenames:
    raise RuntimeError('No data files found.')
  index = int(np.floor(FLAGS.train_val_split * len(filenames)))
  if training:
    filenames = filenames[:index]
  else:
    filenames = filenames[index:]
  filename_queue = tf.train.string_input_producer(filenames, shuffle=True)
  reader = tf.TFRecordReader()
  _, serialized_example = reader.read(filename_queue)

  features = {"image1_raw": tf.FixedLenFeature([1], tf.string),
              "image2_raw": tf.FixedLenFeature([1], tf.string),
              "flo_raw": tf.FixedLenFeature([1], tf.string)}
  features = tf.parse_single_example(serialized_example, features=features)
  image = tf.decode_raw(features['image1_raw'], tf.float32)
  image = tf.reshape(image, [ORIGINAL_HEIGHT, ORIGINAL_WIDTH, COLOR_CHAN])
  
  image2 = tf.decode_raw(features['image2_raw'], tf.float32)
  image2 = tf.reshape(image2, [ORIGINAL_HEIGHT, ORIGINAL_WIDTH, COLOR_CHAN])
  
  flo = tf.decode_raw(features['flo_raw'], tf.float32)
  flo = tf.reshape(flo, [ORIGINAL_HEIGHT, ORIGINAL_WIDTH, 2])
  
  if IMG_HEIGHT != IMG_WIDTH:
    raise ValueError('Unequal height and width unsupported')

  crop_size = min(ORIGINAL_HEIGHT, ORIGINAL_WIDTH)
  image = tf.image.resize_image_with_crop_or_pad(image, crop_size, crop_size)
  image = tf.reshape(image, [1, crop_size, crop_size, COLOR_CHAN])
  
  image2 = tf.image.resize_image_with_crop_or_pad(image2, crop_size, crop_size)
  image2 = tf.reshape(image2, [1, crop_size, crop_size, COLOR_CHAN])
  
  flo = tf.image.resize_image_with_crop_or_pad(flo, crop_size, crop_size)
  flo = tf.reshape(flo, [1, crop_size, crop_size, 2])
  
  flo = tf.maximum(tf.minimum(flo, 15.0), -15.0)
  
  result = tf.cond(tf.reduce_max(tf.reduce_max(flo, axis=[1,2])-tf.reduce_min(flo, axis=[1,2])) < 5.0, lambda: [image[0:0], image2[0:0], flo[0:0]], 
                   lambda: [image, image2, flo])
  
  image_batch = tf.train.shuffle_batch(
    result,
    FLAGS.batch_size,
    num_threads=FLAGS.batch_size,
    capacity=100 * FLAGS.batch_size,
    min_after_dequeue=1600,
    enqueue_many=True)

  return image_batch

