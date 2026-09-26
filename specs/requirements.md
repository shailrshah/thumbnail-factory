# Thumbnail Factory — Requirements

## Purpose

A learning project for Docker and Docker Compose. The app is intentionally small; the
point is that every container has a real job, so each Docker concept shows up because
the app needs it, not because it was bolted on.

A user uploads an image, a background worker generates thumbnails, and the UI shows the
job progressing until the thumbnails are ready.

## Stack

| Service    | Tech                              | Role                                                        |
|------------|-----------------------------------|-------------------------------------------------------------|
| `gateway`  | nginx                             | Single public entry point; routes traffic, serves thumbnails |
| `frontend` | React + Vite (served by nginx)    | Upload UI and job status view                                |
| `backend`  | Python, FastAPI                   | HTTP API; stores uploads, enqueues jobs, reports status      |
| `redis`    | Redis                             | Job queue (RQ) and job status store                          |
| `worker`   | Python, RQ, Pillow                | Consumes jobs, generates thumbnails                          |

`backend` and `worker` share one Python codebase and image, started with different commands.

## Functional requirements

### Upload
- FR1. User can select or drag-and-drop an image in the browser and upload it.
- FR2. Accepted formats: JPEG, PNG, WebP. Max size: 10 MB.
- FR3. Invalid uploads are rejected by the backend with a clear error shown in the UI.

### Processing
- FR4. Each upload creates a job with a unique ID and is enqueued immediately; the upload
  request does not wait for processing.
- FR5. The worker generates thumbnails at widths 128, 256, and 512 px, preserving aspect ratio.
- FR6. Job states: `queued` → `processing` → `done` | `failed`. Failed jobs record an error message.
- FR7. A configurable artificial delay (`WORKER_DELAY_SECONDS`, default 2) makes state
  transitions and multi-worker distribution observable.
- FR8. Each job records which worker processed it (container hostname), so scaling is visible in the UI.

### Viewing
- FR9. UI lists recent jobs (newest first) with status, updating without a manual refresh
  (polling is sufficient).
- FR10. Completed jobs display their thumbnails, served by `gateway` directly from the shared volume.

## API

All routes are served under `/api` by `backend`.

| Method | Path              | Description                                  |
|--------|-------------------|----------------------------------------------|
| POST   | `/api/jobs`       | Multipart upload; returns `{id, status}`     |
| GET    | `/api/jobs`       | Recent jobs (most recent 50)                  |
| GET    | `/api/jobs/{id}`  | Job detail incl. status, worker, thumbnail URLs, error |
| GET    | `/api/health`     | Liveness + Redis connectivity                 |

## Infrastructure requirements (Docker Compose)

- IR1. The whole stack starts with `docker compose up --build` from a fresh clone, with no
  host-installed Python or Node required.
- IR2. Only `gateway` publishes a host port (`8080`). All other services are reachable
  only on internal networks.
- IR3. Two networks:
  - `public`: `gateway`, `frontend`, `backend`
  - `internal`: `backend`, `worker`, `redis`

  `redis` must not be reachable from `gateway` or `frontend`.
- IR4. Gateway routing: `/api/*` → `backend`, `/media/*` → shared volume (read-only), everything else → `frontend`.
- IR5. Named volume `media` holds originals and thumbnails; mounted read-write in `backend`
  and `worker`, read-only in `gateway`.
- IR6. Named volume `redis-data` persists Redis data across restarts.
- IR7. Healthchecks on `redis` and `backend`; dependents use `depends_on` with
  `condition: service_healthy`.
- IR8. `worker` can be scaled: `docker compose up --scale worker=3` must work with no config changes.
- IR9. Restart policy `unless-stopped` on long-running services.
- IR10. Multi-stage builds: `frontend` builds with Node and ships only static assets on nginx;
  Python image does not include build tooling in the final stage.
- IR11. Configuration via environment variables with defaults in `.env.example`; no secrets committed.
- IR12. Containers run as non-root users where the base image allows it.

### Development mode
- IR13. A `compose.override.yml` (auto-loaded) provides a dev setup: source bind mounts,
  FastAPI auto-reload, Vite dev server with HMR proxied through `gateway`.
- IR14. `docker compose -f compose.yml up` runs the production-like setup without overrides.

## Continuous integration (GitHub Actions)

- CI1. Runs on every pull request and every push to `main`.
- CI2. Lint: `ruff` for Python, `oxlint` for the frontend.
- CI3. Unit tests: `pytest` for backend and worker.
- CI4. Build all images with Buildx, using the GitHub Actions cache so unchanged layers are reused.
- CI5. Integration smoke test against the real Compose stack: `docker compose -f compose.yml up -d --wait`,
  upload a sample image through `gateway`, poll until `done`, fetch a thumbnail via `/media`, then tear down.
  Dump `docker compose logs` on failure.
- CI6. `main` is protected in the sense that deployment only runs after CI passes.

## Deployment (AWS)

Goal: run the same Compose stack in the cloud, so the deployment reinforces Compose rather
than replacing it with a different orchestrator.

- D1. Target: a single EC2 instance running Docker and Docker Compose, in the project's selected Region.
- D2. Images are pushed to Amazon ECR, one repository per built image, tagged with the git SHA.
  Lifecycle policy keeps the most recent 10 tags.
- D3. `compose.prod.yml` references ECR images by `IMAGE_TAG` instead of building locally; no bind mounts, no dev overrides.
- D4. GitHub Actions authenticates as a dedicated IAM user, `thumbnail-factory-ci`, whose access keys
  are stored as GitHub secrets. (OIDC is preferred, but the project's free plan SCP denies
  `iam:*Provider*`, so an OIDC identity provider cannot be created.) To contain the risk of long-lived keys:
  - The user's policy allows only: `ecr:GetAuthorizationToken`; image push/pull on this project's ECR
    repositories; `ssm:SendCommand` on the deployment instance with the `AWS-RunShellScript` document;
    `ssm:GetCommandInvocation`.
  - CDK creates the user and policy but not the access keys (keys would otherwise leak into
    CloudFormation state). Keys are created once via the CLI and pasted into GitHub.
  - Secrets live in a GitHub environment named `production` that only `main` can deploy to, so
    pull-request workflows never see them.
  - README documents key rotation.
- D5. Deploys run through SSM Run Command (pull images, `docker compose up -d`). No SSH; port 22 closed.
- D6. Security group allows inbound HTTP (port 80) only. The instance profile grants only ECR pull and SSM.
- D7. All AWS resources are defined as code with AWS CDK (Python) under `infra/`, deployable and
  destroyable with one command each.
- D8. Rollback = re-run the deploy workflow with a previous SHA.
- D9. README documents expected monthly cost and the teardown command.
- D10. Constraints from the AWS free plan:
  - All resources are created in the project's selected Region (`us-east-2`).
  - The instance type must be free-plan eligible; default `t3.small` (x86_64, 2 GiB).
    x86 avoids multi-arch image builds in CI.
  - On-demand only (Spot is denied).

## Learning experiments

The README should walk through these, each with the command to run and what to observe:

1. Scale workers to 3 and upload several images; see jobs spread across worker hostnames.
2. `docker compose kill worker` mid-job; observe the stuck/failed job and restart behavior.
3. `docker compose down -v` vs `down`; see which data survives.
4. Try to reach Redis from `gateway` (`docker compose exec gateway ...`); see network isolation.
5. Inspect image sizes before/after multi-stage builds (`docker image ls`).
6. Break the backend healthcheck; watch dependents wait.
7. Open a PR that breaks the worker; watch the CI smoke test catch it.
8. Deploy an older SHA to the EC2 instance; confirm the rollback.

## Non-goals

- Authentication, multi-user support
- TLS, custom domain, Kubernetes, ECS
- Multiple environments (staging/prod), multi-Region, high availability
- A relational database (Redis is enough for job state; Postgres may be a later extension)
- Automated test coverage beyond basic API and worker tests

## Milestones

1. Backend + Redis + worker running via Compose; jobs processable via `curl`.
2. Gateway routing and shared media volume.
3. Frontend upload + status UI.
4. Dev override with hot reload.
5. Hardening: healthchecks, non-root, restart policies, networks split.
6. README with learning experiments.
7. CI: lint, tests, image builds, Compose smoke test.
8. AWS infrastructure via CDK (ECR, EC2, IAM/OIDC, SSM).
9. CD: build, push to ECR, and deploy on merge to `main`.
