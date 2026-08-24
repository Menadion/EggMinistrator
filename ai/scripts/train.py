import tensorflow as tf
import json
from datetime import datetime, timezone

# Bump MODEL_VERSION for a meaningful change (new classes, new architecture). The timestamp is
# appended automatically so that every run is distinguishable even if nobody bumps it.
MODEL_NAME = "candling-classifier"
MODEL_VERSION = "0.3.0"

train_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset/train", image_size=(224, 224)
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset/val", image_size=(224, 224)
)

test_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset/test", image_size=(224, 224)
)

with open("ai/models/classes.json", "w") as file:
    file.write(json.dumps(train_ds.class_names))

base = tf.keras.applications.MobileNetV2(
    input_shape=(224, 224, 3), include_top=False, weights="imagenet"
)
base.trainable = False

model = tf.keras.Sequential([
    # Augmentation. Shows the model flipped, rotated and zoomed copies of each
    # photo so it learns "an egg is an egg whichever way it sits" instead of
    # memorising the exact framing we happened to shoot.
    #
    # These layers only do anything while training -- Keras switches them off
    # automatically for evaluate() and predict(), so validation and test scores
    # are measured on undistorted images. That is why they live in the model and
    # not in the dataset pipeline.
    #
    # ⚠️ This multiplies VARIATIONS of the eggs we have. It does not invent new
    # eggs. Ten eggs augmented into a hundred images is still a model that has
    # only ever seen ten eggs -- it is not a reason to photograph fewer.
    tf.keras.layers.RandomFlip("horizontal"),
    tf.keras.layers.RandomRotation(0.1),
    tf.keras.layers.RandomZoom(0.1),

    # MobileNetV2 was trained on pixels scaled to -1..1, but
    # image_dataset_from_directory hands over 0..255. Without this the network
    # still runs and still reports an accuracy -- it is just quietly much worse
    # than the photos deserve, which reads as "the dataset is bad."
    #
    # It sits INSIDE the model on purpose: classify.py feeds raw pixels straight
    # from cv2, so keeping the scaling here means inference cannot disagree with
    # training. Put it in the dataset pipeline instead and classify.py would need
    # a matching line that nobody remembers to keep in step.
    tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1),

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