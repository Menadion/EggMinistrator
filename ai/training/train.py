import tensorflow as tf
import json
from datetime import datetime, timezone

# Bump MODEL_VERSION for a meaningful change (new classes, new architecture). The timestamp is
# appended automatically so that every run is distinguishable even if nobody bumps it.
MODEL_NAME = "candling-classifier"
MODEL_VERSION = "0.3.0"

train_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset", image_size=(224, 224),
    validation_split=0.2, subset="training", seed=123,
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset", image_size=(224, 224),
    validation_split=0.2, subset="validation", seed=123,
)

half = len(val_ds) // 2
test_ds = val_ds.take(half)
val_ds = val_ds.skip(half)

with open("ai/models/classes.json", "w") as file:
    file.write(json.dumps(train_ds.class_names))

base = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3), include_top=False, weights="imagenet"
)
base.trainable = False

model = tf.keras.Sequential([
    base,
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dense(len(train_ds.class_names), activation="softmax"),
])
model.summary()

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

model.fit(train_ds, validation_data=val_ds, epochs=3)
model.evaluate(test_ds)
model.save("ai/models/egg.keras")

# Written in the same run that saved the weights above, so the version can never describe a
# different model than the one on disk. classify.py reports it; the database stores it.
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

with open("ai/models/version.json", "w") as file:
    file.write(json.dumps({"name": MODEL_NAME, "version": f"{MODEL_VERSION}+{stamp}"}))