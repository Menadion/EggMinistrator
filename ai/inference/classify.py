import sys
import json

result = {"image": sys.argv[1], "class": "defective", "confidence": 0.91}

print(json.dumps(result))