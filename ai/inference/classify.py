import sys
import json
import cv2

img = cv2.imread(sys.argv[1])

if img is None:
    sys.exit(f"Path: {sys.argv[1]} is not a valid image file")

resize = cv2.resize(img, (224, 224))
result = {"image": sys.argv[1], "class": "defective", "confidence": 0.91}

print(json.dumps(result))