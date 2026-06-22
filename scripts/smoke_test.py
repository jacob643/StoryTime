#!/usr/bin/env python3
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_binary():
    dist = os.path.join(ROOT, "dist")
    if not os.path.isdir(dist):
        return None
    for entry in sorted(os.listdir(dist)):
        path = os.path.join(dist, entry)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def main():
    if len(sys.argv) > 1:
        binary = sys.argv[1]
    else:
        binary = _find_binary()

    if not binary or not os.path.isfile(binary):
        print("Smoke test failed — no binary found. Pass the path or run build.py first.", file=sys.stderr)
        sys.exit(1)

    port = _get_free_port()
    env = {**os.environ, "STORYTIME_PORT": str(port)}
    proc = subprocess.Popen([binary], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
                if resp.status == 200:
                    print(f"Smoke test passed — http://127.0.0.1:{port}/ returned 200")
                    return
            except (urllib.error.URLError, urllib.error.HTTPError, ConnectionResetError):
                pass
            time.sleep(0.5)
        print("Smoke test failed — no 200 response within 15 seconds", file=sys.stderr)
        sys.exit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
