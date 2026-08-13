import tensorflow as tf
import numpy as np
import sys
import json
import time
import cv2

model = tf.keras.models.load_model("ai/models/egg.keras")

with open("ai/models/classes.json") as file:
    CLASSES = json.load(file)

with open("ai/models/version.json") as file:
    MODEL = json.load(file)

img = cv2.imread(sys.argv[1])

if img is None:
    sys.exit(f"Path: {sys.argv[1]} is not a valid image file")

resize = cv2.resize(img, (224, 224))

rgb = cv2.cvtColor(resize, cv2.COLOR_BGR2RGB)
batch = np.expand_dims(rgb, 0)

start = time.perf_counter()
probs = model.predict(batch, verbose=0)[0]
elapsed_ms = round((time.perf_counter() - start) * 1000)

result = {
    "image": sys.argv[1],
    "class": CLASSES[probs.argmax()],
    "confidence": float(probs.max()),
    "model_name": MODEL["name"],
    "model_version": MODEL["version"],
    "inference_time_ms": elapsed_ms,
}

print(json.dumps(result))