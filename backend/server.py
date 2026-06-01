"""Frozen-server entry point.

PyInstaller freezes this into the ``stockbrain-server`` sidecar that Electron spawns. It
just runs the FastAPI app under uvicorn (no reload/workers — those don't work frozen).
"""

from __future__ import annotations

import argparse

import uvicorn

from backend.main import app


def main() -> None:
    parser = argparse.ArgumentParser(prog="stockbrain-server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
