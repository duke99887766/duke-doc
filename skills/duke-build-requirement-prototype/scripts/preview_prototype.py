#!/usr/bin/env python3
"""Serve one HTML prototype from localhost for browser-based validation."""

from __future__ import annotations

import argparse
import functools
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote


class QuietHandler(SimpleHTTPRequestHandler):
    verbose = False

    def log_message(self, format: str, *args: object) -> None:
        if self.verbose:
            super().log_message(format, *args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_file", type=Path)
    parser.add_argument("--root", type=Path, help="Directory to expose; defaults to the HTML file directory.")
    parser.add_argument("--port", type=int, default=0, help="Local port; 0 selects an available port.")
    parser.add_argument("--timeout", type=float, default=0, help="Stop automatically after N seconds; 0 waits for Ctrl+C.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    html_file = args.html_file.resolve()
    if not html_file.is_file():
        print(f"ERROR: 文件不存在：{html_file}")
        return 2
    if html_file.suffix.lower() not in {".html", ".htm"}:
        print(f"ERROR: 不是HTML文件：{html_file}")
        return 2
    if not 0 <= args.port <= 65535:
        print(f"ERROR: 端口范围无效：{args.port}")
        return 2
    if args.timeout < 0:
        print("ERROR: timeout 不能小于 0。")
        return 2

    root = args.root.resolve() if args.root else html_file.parent
    if not root.is_dir():
        print(f"ERROR: 预览根目录不存在：{root}")
        return 2
    try:
        relative_file = html_file.relative_to(root)
    except ValueError:
        print(f"ERROR: HTML文件不在预览根目录内：{html_file}")
        return 2

    QuietHandler.verbose = args.verbose
    handler = functools.partial(QuietHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    server.daemon_threads = True
    server.timeout = 0.25
    url = f"http://127.0.0.1:{server.server_port}/{quote(relative_file.as_posix())}"

    print(f"PREVIEW_URL: {url}", flush=True)
    print(f"PREVIEW_ROOT: {root}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    try:
        if args.timeout:
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                server.handle_request()
        else:
            server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
