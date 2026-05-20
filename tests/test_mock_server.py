import requests

from futureagi_sdk_test_harness.mock_server import MockFutureAgiServer


def test_mock_server_records_matching_request():
    server = MockFutureAgiServer(
        [
            {
                "id": "ping",
                "method": "POST",
                "path": "/ping",
                "response": {"ok": True},
            }
        ]
    ).start()
    try:
        response = requests.post(
            f"{server.url}/ping",
            headers={"X-Api-Key": "key"},
            json={"hello": "world"},
            timeout=5,
        )
        assert response.json() == {"ok": True}
        [recorded] = server.requests_for("ping")
        assert recorded.headers["X-Api-Key"] == "key"
        assert recorded.json == {"hello": "world"}
    finally:
        server.stop()
