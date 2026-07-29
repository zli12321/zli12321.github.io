"""Local static server for the dashboard.

`python -m http.server` works too, but it caches aggressively and serves from the
current directory, which makes it easy to view a stale build. This serves
`site/` explicitly with caching disabled.
"""

from __future__ import annotations

import functools
import http.server
import socket
import socketserver
import webbrowser
from pathlib import Path


class _Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        if isinstance(args[1] if len(args) > 1 else "", str) and str(args[1]).startswith("4"):
            super().log_message(format, *args)


class _Server(socketserver.TCPServer):
    allow_reuse_address = True


def serve(
    directory: Path, *, host: str = "127.0.0.1", port: int = 8000, open_browser: bool = False
) -> None:
    if not directory.is_dir():
        raise SystemExit(f"{directory} does not exist")
    if not (directory / "index.html").is_file():
        raise SystemExit(f"{directory} has no index.html")

    handler = functools.partial(_Handler, directory=str(directory))
    try:
        server = _Server((host, port), handler)
    except OSError as error:
        raise SystemExit(
            f"Could not bind {host}:{port} ({error}). Try another port with --port."
        ) from error

    url = f"http://{host}:{port}/"
    print(f"Serving {directory} at {url}")
    if not (directory / "data" / "radar.json").is_file():
        print("Warning: site/data/radar.json is missing. Run 'vlm-radar rebuild' first.")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


def free_port(preferred: int = 8000, *, host: str = "127.0.0.1") -> int:
    """Return `preferred` if it is available, otherwise an ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return probe.getsockname()[1]
