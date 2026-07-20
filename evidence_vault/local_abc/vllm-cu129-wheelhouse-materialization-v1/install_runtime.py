from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--venv", type=Path, required=True)
    args = parser.parse_args()
    if args.venv.exists():
        raise SystemExit("target virtual environment already exists")
    venv.EnvBuilder(with_pip=True, clear=False).create(args.venv)
    python = args.venv / "bin" / "python"
    command = [
        str(python),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(args.wheelhouse),
        "--require-hashes",
        "-r",
        str(args.lock),
    ]
    result = subprocess.run(command, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
