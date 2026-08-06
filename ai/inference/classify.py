import tensorflow as tf
import numpy as np
import sys
import json
import cv2

model = tf.keras.models.load_model("ai/models/egg.keras")

with open("ai/models/classes.json") as file:
    CLASSES = json.load(file)

img = cv2.imread(sys.argv[1])

if img is None:
    sys.exit(f"Path: {sys.argv[1]} is not a valid image file")

resize = cv2.resize(img, (224, 224))

rgb = cv2.cvtColor(resize, cv2.COLOR_BGR2RGB)
batch = np.expand_dims(rgb, 0)

probs = model.predict(batch, verbose=0)[0]

result = {"image": sys.argv[1], "class": CLASSES[probs.argmax()], "confidence": float(probs.max())}

print(json.dumps(result))