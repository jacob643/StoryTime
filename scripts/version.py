#!/usr/bin/env python3
"""CLI tool to bump the version across all versioned files.

Usage:
    python scripts/version.py bump 0.2.0
    python scripts/version.py show

Reads current version from backend/_version.py, rewrites files,
and prints the diff.
"""

import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "backend" / "_version.py"
CHANGELOG = ROOT / "CHANGELOG.md"
PYPROJECT = ROOT / "pyproject.toml"


def get_current_version() -> str:
    match = re.search(r'__version__\s*=\s*"([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("Could not find version in _version.py")
    return match.group(1)


def show():
    print(get_current_version())


def bump(new_version: str):
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"error: '{new_version}' is not a valid semver (x.y.z)", file=sys.stderr)
        sys.exit(1)

    old = get_current_version()
    print(f"  {old} -> {new_version}")

    # _version.py
    text = VERSION_FILE.read_text(encoding="utf-8")
    text = re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new_version}"', text)
    VERSION_FILE.write_text(text, encoding="utf-8")
    print(f"  wrote {VERSION_FILE.relative_to(ROOT)}")

    # pyproject.toml
    text = PYPROJECT.read_text(encoding="utf-8")
    text = re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{new_version}"', text, flags=re.MULTILINE)
    PYPROJECT.write_text(text, encoding="utf-8")
    print(f"  wrote {PYPROJECT.relative_to(ROOT)}")

    # CHANGELOG.md — move [Unreleased] body into new version section
    text = CHANGELOG.read_text(encoding="utf-8")
    header = f"## [{new_version}]"
    if header not in text:
        today = datetime.date.today().isoformat()
        # Capture the body between [Unreleased] and the next ## or end
        unreleased_match = re.search(
            r"^## \[Unreleased\].*?\n(.*?)(?=^## |\Z)",
            text, re.DOTALL | re.MULTILINE,
        )
        body = unreleased_match.group(1).lstrip("\n") if unreleased_match else ""

        fresh_unreleased = "## [Unreleased]\n### Added\n### Changed\n### Deprecated\n### Removed\n### Fixed\n### Security\n"
        new_section = f"{header} - {today}\n\n{body}" if body else f"{header} - {today}\n"

        replacement = fresh_unreleased + "\n" + new_section

        if unreleased_match:
            text = text[:unreleased_match.start()] + replacement + text[unreleased_match.end():]
        else:
            first_header = text.find("\n## [")
            if first_header == -1:
                first_header = len(text)
            text = text[:first_header] + f"\n\n{fresh_unreleased}\n{new_section}" + text[first_header:]

        CHANGELOG.write_text(text, encoding="utf-8")
        print(f"  updated {CHANGELOG.relative_to(ROOT)} (moved content to {new_version} section)")
    else:
        print(f"  {CHANGELOG.relative_to(ROOT)} already has [{new_version}] section")

    print("\nDone. Review with:")
    print(f"  git diff")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "show":
        show()
    elif command == "bump":
        if len(sys.argv) < 3:
            print("Usage: python scripts/version.py bump <version>", file=sys.stderr)
            sys.exit(1)
        bump(sys.argv[2])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)
