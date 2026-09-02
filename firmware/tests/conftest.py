import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_port(port, seconds=10.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.1)
    return False


@pytest.fixture
def stub():
    """Spawn firmware/stub_server.py on a free port with auto-verdicts off.
    Yields the base URL. Kills the process afterwards."""
    port = free_port()
    env = {**os.environ, "STUB_PORT": str(port), "STUB_AUTO_VERDICT": "off"}
    process = subprocess.Popen([sys.executable, str(REPO_ROOT / "firmware" / "stub_server.py")], cwd=REPO_ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert wait_for_port(port), "stub server did not come up"
        yield f"http://127.0.0.1:{port}"
    finally:
        process.kill()
        process.wait()
