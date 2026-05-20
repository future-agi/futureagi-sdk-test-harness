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
| `POST /annotation/metadata` | Fetch annotation labels and projects through the SDK. |
| `POST /annotation-queue/lifecycle` | Run the queue create/add/submit/complete/export e2e flow. |
| `POST /annotation-queue/management` | Run queue CRUD, label CRUD, item assignment/import/skip/remove, analytics/agreement, and export-to-dataset. |
| `POST /annotation-score/lifecycle` | Run score create/bulk/fetch e2e flow. |
| `POST /dataset/lifecycle` | Run dataset create/add-columns/add-rows e2e flow. |
| `POST /dataset/management` | Run dataset lookup, column lookup, run-prompt, eval stats, optimisation, and delete flow. |
| `POST /knowledge-base/lifecycle` | Run KB create/update/delete-files/delete flow without file uploads. |
| `POST /prompt/lifecycle` | Run prompt generate/improve/create/commit/label/fetch/delete flow. |
| `POST /provider-api-key/lifecycle` | Run provider API key set/list/get flow. |

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

When the adapter runs inside Docker and the harness runs on the host, expose the
mock API through Docker's host gateway:

```bash
futureagi-sdk-test-harness run \
  --adapter-url http://localhost:8080 \
  --mock-bind-host 0.0.0.0 \
  --mock-public-host host.docker.internal
```

## Test

```bash
uv run --extra dev pytest -q
```

## Status

The Python and TypeScript adapters currently pass:

- `auth_raw_request`
- `annotation_bulk_log`
- `annotation_metadata_lifecycle_e2e`
- `annotation_queue_lifecycle_e2e`
- `annotation_queue_management_lifecycle_e2e`
- `annotation_score_lifecycle_e2e`
- `dataset_lifecycle_e2e`
- `dataset_management_lifecycle_e2e`
- `knowledge_base_lifecycle_e2e`
- `prompt_lifecycle_e2e`
- `provider_api_key_lifecycle_e2e`

Model logging is intentionally not in the current stable contract: the current
backend does not expose `/sdk/api/v1/log/model/` or `/log/model/`.

Once stable, add adapters for:

- `traceAI`
- `agent-command-center-sdk`
- `agent-opt`
- `ai-evaluation`
- `simulate-sdk`
