# Future AGI SDK Test Harness

Language-agnostic compliance harness for Future AGI SDKs.

The harness runs a mock Future AGI API, drives an SDK adapter over HTTP, records
the SDK's outbound requests, and validates behavior against a shared contract.

This follows the same shape as PostHog's SDK compliance harness:

```text
SDK adapter container
  <-> compliance harness
  <-> mock Future AGI API
  <-> CONTRACT.yaml
```

## Adapter Contract

Every SDK adapter is a tiny HTTP service around the SDK under test.

Required endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Return SDK name, version, language, adapter version, and capabilities. |
| `POST /init` | Initialize SDK credentials and base URL. |
| `POST /reset` | Clear adapter state. |
| `GET /state` | Return adapter-observed state. |

MVP feature endpoints:

| Endpoint | Purpose |
| --- | --- |
| `POST /raw-request` | Make a low-level SDK authenticated request. |
| `POST /annotation/log` | Log Future AGI annotation records through the SDK. |
| `POST /annotation-queue/lifecycle` | Run the queue create/add/submit/complete/export e2e flow. |

## Local Usage

```bash
cd futureagi-sdk-test-harness
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
futureagi-sdk-test-harness run --adapter-url http://localhost:8080
```

The adapter must already be running. The harness will start its own mock Future
AGI API on a free local port and pass that URL to the adapter through `/init`.

## Test

```bash
uv run --extra dev pytest -q
```

## Status

This is the MVP skeleton with the first Python adapter passing:

- `auth_raw_request`
- `annotation_bulk_log`
- `annotation_queue_lifecycle_e2e`

Once stable, add adapters for:

- `traceAI`
- `agent-command-center-sdk`
- `agent-opt`
- `ai-evaluation`
- `simulate-sdk`
