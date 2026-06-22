#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Build Story Time binary with PyInstaller")
    parser.add_argument("--clean", action="store_true", help="remove dist/ and build/ before building")
    parser.add_argument("--skip-smoke", action="store_true", help="skip post-build smoke test")
    args = parser.parse_args()

    sys.path.insert(0, ROOT)
    from backend._version import __version__

    print(f"Building Story Time v{__version__}")

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    if args.clean:
        for d in ["dist", "build"]:
            path = os.path.join(ROOT, d)
            if os.path.isdir(path):
                print(f"Removing {d}/")
                shutil.rmtree(path)

    spec_path = os.path.join(ROOT, "storytime.spec")
    print(f"Running PyInstaller on {spec_path}")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", spec_path], cwd=ROOT)

    dist_dir = os.path.join(ROOT, "dist")
    if os.path.isdir(dist_dir):
        for entry in sorted(os.listdir(dist_dir)):
            entry_path = os.path.join(dist_dir, entry)
            if os.path.isfile(entry_path):
                size = os.path.getsize(entry_path)
                print(f"Output: {entry} ({size / 1024 / 1024:.1f} MB)")

    if not args.skip_smoke:
        smoke_path = os.path.join(ROOT, "scripts", "smoke_test.py")
        if os.path.isfile(smoke_path):
            print("Running smoke test...")
            subprocess.check_call([sys.executable, smoke_path], cwd=ROOT)

    print("Build complete.")


if __name__ == "__main__":
    main()
