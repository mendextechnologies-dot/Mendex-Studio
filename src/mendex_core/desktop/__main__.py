"""Private bounded JSON-lines desktop transport. No network listener or arbitrary invocation."""
import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from ..paths import default_data_root
from ..service import StudioService
from .models import BridgeRequest, PROTOCOL_VERSION
from .service import DesktopService

MAX_REQUEST = 256 * 1024
MAX_RESPONSE = 8 * 1024 * 1024


def serve(service, input_stream, output_stream):
    lock, pending_lock = Lock(), Lock()
    pending = set()

    def send(payload):
        text = json.dumps(payload, allow_nan=False, separators=(",", ":"))
        if len(text.encode("utf-8")) > MAX_RESPONSE:
            text = json.dumps({"protocol_version": PROTOCOL_VERSION, "id": payload.get("id"), "error": {"code": "RESPONSE_TOO_LARGE", "message": "Response exceeds 8 MiB; choose a narrower view"}})
        with lock:
            output_stream.write(text + "\n")
            output_stream.flush()

    def execute(request):
        try:
            result = service.dispatch(request.method, request.params)
            send({"protocol_version": PROTOCOL_VERSION, "id": request.id, "result": result})
        except Exception as exc:
            logging.getLogger("mendex.desktop").warning("Desktop request failed: %s", type(exc).__name__)
            send({"protocol_version": PROTOCOL_VERSION, "id": request.id, "error": {"code": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)}})
        finally:
            with pending_lock:
                pending.discard(request.id)

    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="mendex-read") as pool:
        while True:
            line = input_stream.readline(MAX_REQUEST + 1)
            if not line:
                break
            try:
                if len(line.encode("utf-8")) > MAX_REQUEST:
                    # Drain the rest of this malformed frame without treating its suffix as a request.
                    while line and not line.endswith("\n"):
                        line = input_stream.readline(MAX_REQUEST + 1)
                    raise ValueError("Request exceeds 256 KiB")
                request = BridgeRequest.model_validate_json(line)
                with pending_lock:
                    if request.id in pending or len(pending) >= 16:
                        raise ValueError("Request ID is pending or desktop request capacity reached")
                    pending.add(request.id)
            except Exception as exc:
                send({"protocol_version": PROTOCOL_VERSION, "id": None, "error": {"code": "INVALID_INPUT", "message": str(exc)}})
                continue
            if request.method in ("handshake", "shutdown"):
                execute(request)
                if request.method == "shutdown":
                    break
            else:
                pool.submit(execute, request)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    service = DesktopService(StudioService(args.root or default_data_root()))
    serve(service, sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
