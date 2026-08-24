"""Print the class list Keras derives from each split, and say whether they agree.

The folder names ARE the labels. Keras sorts them alphabetically and hands the
model 0, 1, 2 -- so a typo or a missing class folder silently renumbers the
labels instead of raising. Nothing errors; the model just reports the wrong
class with full confidence.

Since 2026-08-23 the dataset is split three ways on disk, and train.py reads
each split as its own folder. That means there are now THREE folders that each
produce a class list, and they have to be identical. classes.json is written
from train/ alone, so if test/ disagrees, evaluate() scores against a different
numbering than the model was fitted to.

Run this after adding, renaming or deleting any class folder.

    py ai/scripts/check_order.py
"""

import tensorflow as tf

SPLITS = ["train", "val", "test"]

class_names = {}
for split in SPLITS:
    dataset = tf.keras.utils.image_dataset_from_directory(f"ai/dataset/{split}")
    class_names[split] = dataset.class_names
    print(f"{split}: {dataset.class_names}")

print()
if class_names["train"] == class_names["val"] == class_names["test"]:
    print("OK - all three splits agree on the class names and their order.")
else:
    print("MISMATCH - the three splits do not agree.")
    print("Fix the folder names before training. classes.json is written from")
    print("train/, so any split that disagrees is scored against the wrong labels.")
