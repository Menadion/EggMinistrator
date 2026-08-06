import tensorflow as tf
import json

train_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset", image_size=(224, 224),
    validation_split=0.2, subset="training", seed=123,
)

val_ds = tf.keras.utils.image_dataset_from_directory(
    "ai/dataset", image_size=(224, 224),
    validation_split=0.2, subset="validation", seed=123,
)

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

model.save("ai/models/egg.keras")