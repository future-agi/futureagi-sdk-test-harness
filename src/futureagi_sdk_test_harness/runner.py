from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import requests

from futureagi_sdk_test_harness.contract import Contract
from futureagi_sdk_test_harness.mock_server import MockFutureAgiServer, RecordedRequest


@dataclass
class SuiteResult:
    id: str
    name: str
    passed: bool
    skipped: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    passed: bool
    suite_results: list[SuiteResult]


class HarnessRunner:
    def __init__(self, contract: Contract, adapter_url: str):
        self.contract = contract
        self.adapter_url = adapter_url.rstrip("/")

    def run(self) -> RunResult:
        health = self._adapter_request("GET", "/health").json()
        capabilities = set(health.get("capabilities") or [])
        results: list[SuiteResult] = []

        for suite in self.contract.suites:
            suite_id = suite["id"]
            required = set(suite.get("requires") or [])
            missing = sorted(required - capabilities)
            if missing:
                results.append(
                    SuiteResult(
                        id=suite_id,
                        name=suite.get("name", suite_id),
                        passed=True,
                        skipped=True,
                        errors=[f"Missing capabilities: {', '.join(missing)}"],
                    )
                )
                continue

            results.append(self._run_suite(suite))

        return RunResult(
            passed=all(result.passed for result in results if not result.skipped),
            suite_results=results,
        )

    def _run_suite(self, suite: dict[str, Any]) -> SuiteResult:
        suite_id = suite["id"]
        mock = MockFutureAgiServer(suite.get("mock") or []).start()
        errors: list[str] = []
        action_results: dict[str, Any] = {}
        try:
            for action in suite.get("actions") or []:
                body = dict(action.get("body") or {})
                if action.get("endpoint") == "/init":
                    body["base_url"] = mock.url
                response = self._adapter_request(
                    method=action.get("method", "POST"),
                    endpoint=action["endpoint"],
                    json_body=body,
                )
                try:
                    action_results[str(action.get("id") or action["endpoint"])] = response.json()
                except ValueError:
                    action_results[str(action.get("id") or action["endpoint"])] = response.text
                if not (200 <= response.status_code < 300):
                    errors.append(
                        f"Action {action.get('id', action['endpoint'])} failed: "
                        f"HTTP {response.status_code} {response.text}"
                    )

            for assertion in suite.get("assertions") or []:
                errors.extend(self._assert(mock, assertion, action_results))
        finally:
            mock.stop()

        return SuiteResult(
            id=suite_id,
            name=suite.get("name", suite_id),
            passed=not errors,
            errors=errors,
        )

    def _adapter_request(
        self,
        method: str,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
    ) -> requests.Response:
        return requests.request(
            method=method.upper(),
            url=f"{self.adapter_url}{endpoint}",
            json=json_body,
            timeout=30,
        )

    def _assert(
        self,
        mock: MockFutureAgiServer,
        assertion: dict[str, Any],
        action_results: dict[str, Any],
    ) -> list[str]:
        assertion_type = assertion["type"]
        if assertion_type == "action_result":
            return _assert_action_result(action_results, assertion)
        if assertion_type != "mock_request":
            return [f"Unsupported assertion type: {assertion_type}"]

        request_id = assertion["request_id"]
        requests_for_id = mock.requests_for(request_id)
        errors: list[str] = []

        if "count" in assertion and len(requests_for_id) != int(assertion["count"]):
            errors.append(
                f"{request_id}: expected {assertion['count']} requests, got {len(requests_for_id)}"
            )
        if "min_count" in assertion and len(requests_for_id) < int(assertion["min_count"]):
            errors.append(
                f"{request_id}: expected at least {assertion['min_count']} requests, "
                f"got {len(requests_for_id)}"
            )

        if not requests_for_id:
            return errors

        request = requests_for_id[-1]
        errors.extend(_assert_headers(request, assertion.get("headers") or {}))

        if "json_contains" in assertion:
            expected = assertion["json_contains"]
            if not _contains(request.json, expected):
                errors.append(
                    f"{request_id}: JSON body did not contain expected subset.\n"
                    f"Expected subset: {json.dumps(expected, sort_keys=True)}\n"
                    f"Actual: {json.dumps(request.json, sort_keys=True)}"
                )

        if "query" in assertion:
            for param, expected in assertion["query"].items():
                actual_values = request.query.get(param, [])
                if str(expected) not in actual_values:
                    errors.append(
                        f"{request_id}: expected query {param}={expected}, got {actual_values}"
                    )

        return errors


def _assert_headers(request: RecordedRequest, expected: dict[str, str]) -> list[str]:
    errors: list[str] = []
    lower_headers = {key.lower(): value for key, value in request.headers.items()}
    for header, value in expected.items():
        actual = lower_headers.get(header.lower())
        if actual != value:
            errors.append(f"{request.request_id}: expected header {header}={value}, got {actual}")
    return errors


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        for key, value in expected.items():
            if key not in actual or not _contains(actual[key], value):
                return False
        return True
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False
        return all(
            any(_contains(actual_item, expected_item) for actual_item in actual)
            for expected_item in expected
        )
    return actual == expected


def _assert_action_result(
    action_results: dict[str, Any],
    assertion: dict[str, Any],
) -> list[str]:
    action_id = str(assertion["action_id"])
    if action_id not in action_results:
        return [f"{action_id}: action result not found"]

    actual = _path_get(action_results[action_id], str(assertion["path"]))
    expected = assertion.get("expected")
    if actual != expected:
        return [f"{action_id}: expected {assertion['path']}={expected!r}, got {actual!r}"]
    return []


def _path_get(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            return None
    return current
