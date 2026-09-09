# Claims Intake Service

The claims intake service accepts a first notice of loss from the claims
portal. It checks the payload against the policy master and the rules in
`docs/api-contract.md`, then either records the notification and issues a
claim reference or refuses it with a specific reason. It does not adjust,
reserve, or decide whether a claim will be paid.

`docs/api-contract.md` is the authority on what the service accepts, what it
returns, and under what conditions it refuses.

## Where things are


| Path                         | What it holds                                                     |
| ---------------------------- | ----------------------------------------------------------------- |
| `docs/api-contract.md`       | What the service accepts, returns, and refuses. The authority.    |
| `docs/requirements-brief.md` | The open work items and their acceptance criteria.                |
| `data/`                      | Synthetic policies and notification payloads.                     |
| `src/claims/`                | The service. HTTP lives in `src/claims/api/routes.py`.            |
| `tests/`                     | Unit tests mirror `src/claims/`. Integration tests exercise HTTP. |
| `Dockerfile`                 | Image that runs the service.                                      |




## Working in this repository

You are inside a Linux container. Confirm it before you start:

```
uname -sm     # Linux aarch64
pwd           # /workspaces/claims-intake
```

Dependencies are installed when the container is created. There is no install
step in any assignment this week. If a tool you need is missing, that is a defect
in the image specification and should be reported rather than worked around.

## Run the tests

From this directory:

```
uv run pytest
uv run ruff check .
uv run mypy
```

`uv run pytest` runs the unit suite and `tests/integration/test_routes.py`,
which posts to `POST /notifications` instead of calling service functions.

## Run the service

From this directory:
`uv run uvicorn claims.api.routes:app --host 0.0.0.0 --port 8000`

The listener is `http://localhost:8000`. 

Submit a notification:
`curl -s -X POST http://localhost:8000/notifications -H 'Content-Type: application/json' -d '{"policy_number":"MOT-4471","loss_date":"2026-04-02","claim_type":"collision","estimated_amount":"4200.00"}'`

A well-formed, admissible notice returns `201` with a `claim_reference` such
as `CLM-2026-000001` and `"status": "recorded"`. A refusal returns the error
envelope in contract section 5. Recorded notifications are held in memory
and are gone when the process stops.

## Run with Docker

Build the image from this directory:
`docker buildx build --platform linux/amd64 -t claims-intake .`

`--platform linux/amd64` is there because Docker builds for the machine you are on unless you say otherwise. The flag tells Buildx to use an amd64 image even if you built it on a laptop that is not amd64. A Mac with Apple Silicon produces an ARM image by default. The machines that run this service are amd64.

Then:
`docker run --rm -p 8000:8000 claims-intake`

`.dockerignore` builds context while ignoring unnecessary files.

## Data

Everything in `data/` is synthetic and was authored for this program. It contains
no real client data and no named clients.