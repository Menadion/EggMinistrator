import tensorflow as tf

ds = tf.keras.utils.image_dataset_from_directory("ai/dataset")
print(ds.class_names)
