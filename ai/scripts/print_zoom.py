"""Print the zoom capture.py last saved, or print nothing at all.

run-eggministrator.bat feeds this to listen_station.py --zoom so the station
crops exactly the way the dataset was shot. If those two ever disagree the
model infers on a framing it never trained on, and nothing about the failure
looks like a framing problem.

Lives in a file rather than inline in the .bat because a Python one-liner is
full of brackets and quotes, and cmd treats an unescaped ')' inside an if-block
as the end of the block.

Prints nothing and exits 0 when there is no usable saved zoom, so the caller
can fall back to the listener's own default.
"""

import json
from pathlib import Path

SETTINGS_PATH = Path("ai/capture_settings.json")

try:
    saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    zoom = saved.get("zoom") if isinstance(saved, dict) else None
except (OSError, ValueError):
    zoom = None

# bool is a subclass of int, so exclude it explicitly -- True would print as
# "True" and become an unparseable --zoom argument.
if isinstance(zoom, (int, float)) and not isinstance(zoom, bool):
    print(zoom)
