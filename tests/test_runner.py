from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from futureagi_sdk_test_harness.contract import Contract, load_contract
from futureagi_sdk_test_harness.runner import HarnessRunner


def test_runner_skips_missing_capabilities():
    adapter = _FakeAdapter(capabilities=[]).start()
    try:
        result = HarnessRunner(load_contract(), adapter.url).run()
        assert result.passed
        assert all(suite.skipped for suite in result.suite_results)
    finally:
        adapter.stop()


def test_runner_asserts_action_results():
    adapter = _FakeAdapter(capabilities=["demo"]).start()
    contract = Contract(
        version="test",
        name="test",
        suites=[
            {
                "id": "demo_suite",
                "name": "Demo suite",
                "requires": ["demo"],
                "actions": [
                    {
                        "id": "ok",
                        "method": "POST",
                        "endpoint": "/ok",
                        "body": {},
                    }
                ],
                "assertions": [
                    {
                        "type": "action_result",
                        "action_id": "ok",
                        "path": "nested.value",
                        "expected": 42,
                    }
                ],
            }
        ],
    )
    try:
        result = HarnessRunner(contract, adapter.url).run()
        assert result.passed
        assert result.suite_results[0].errors == []
    finally:
        adapter.stop()


class _FakeAdapter:
    def __init__(self, capabilities: list[str]):
        self.capabilities = capabilities
        self.url = ""
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> "_FakeAdapter":
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self._write({"capabilities": parent.capabilities})
                else:
                    self._write({"error": "not found"}, status=404)

            def do_POST(self) -> None:  # noqa: N802
                if self.path == "/ok":
                    self._write({"success": True, "nested": {"value": 42}})
                else:
                    self._write({"error": "not found"}, status=404)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def _write(self, payload: Any, status: int = 200) -> None:
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)
