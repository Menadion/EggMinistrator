"""Make `import capture`, `import station_common` etc. resolve the way the
listeners do when run from the repo root (`py ai/listen_station.py` puts ai/ on
sys.path implicitly; pytest does not)."""
import sys
from pathlib import Path

AI_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_DIR.parent
for folder in (AI_DIR, AI_DIR / "scripts"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
