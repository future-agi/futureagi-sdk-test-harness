from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class RecordedRequest:
    request_id: str | None
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    json: Any = None
    body: str = ""


@dataclass
class MockExpectation:
    id: str
    method: str
    path: str
    status: int = 200
    response: Any = field(default_factory=dict)


class MockFutureAgiServer:
    def __init__(self, expectations: list[dict[str, Any]]):
        self.expectations = [
            MockExpectation(
                id=item["id"],
                method=item["method"].upper(),
                path=item["path"],
                status=int(item.get("status", 200)),
                response=item.get("response", {}),
            )
            for item in expectations
        ]
        self.requests: list[RecordedRequest] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.url: str = ""

    def start(self) -> "MockFutureAgiServer":
        port = _free_port()
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                self._handle()

            def do_POST(self) -> None:  # noqa: N802
                self._handle()

            def do_PATCH(self) -> None:  # noqa: N802
                self._handle()

            def do_PUT(self) -> None:  # noqa: N802
                self._handle()

            def do_DELETE(self) -> None:  # noqa: N802
                self._handle()

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def _handle(self) -> None:
                parsed = urlparse(self.path)
                body = self.rfile.read(int(self.headers.get("content-length", "0") or "0"))
                body_text = body.decode("utf-8") if body else ""
                json_body = _parse_json(body_text)
                expectation = parent._match(self.command, parsed.path)

                parent.requests.append(
                    RecordedRequest(
                        request_id=expectation.id if expectation else None,
                        method=self.command,
                        path=parsed.path,
                        query=parse_qs(parsed.query),
                        headers={key: value for key, value in self.headers.items()},
                        json=json_body,
                        body=body_text,
                    )
                )

                if expectation is None:
                    self._write_json(
                        404,
                        {
                            "status": False,
                            "type": "not_found",
                            "code": "unexpected_mock_request",
                            "detail": f"No mock expectation for {self.command} {parsed.path}",
                        },
                    )
                    return

                self._write_json(expectation.status, expectation.response)

            def _write_json(self, status: int, payload: Any) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.url = f"http://127.0.0.1:{port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)

    def requests_for(self, request_id: str) -> list[RecordedRequest]:
        return [request for request in self.requests if request.request_id == request_id]

    def _match(self, method: str, path: str) -> MockExpectation | None:
        for expectation in self.expectations:
            if expectation.method == method.upper() and expectation.path == path:
                return expectation
        return None


def _parse_json(body: str) -> Any:
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
