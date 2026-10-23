# FlowForge

Event-driven workflow automation engine built with Django.

[![CI](https://github.com/KIRAZINA/flowforge/actions/workflows/ci.yml/badge.svg)](https://github.com/KIRAZINA/flowforge/actions/workflows/ci.yml)

FlowForge is an open-source, event-driven workflow automation platform in the spirit of n8n and Make. It lets you model workflows as directed acyclic graphs of typed nodes, execute them synchronously or asynchronously, and trigger them via webhooks, schedules, or the REST API. Workflows run inside a restricted Python sandbox for safe user-provided transformations.

## Key Features

- Visual-ready DAG model: `Workflow`, `WorkflowVersion`, `Node`, `Edge`, `Trigger`
- Synchronous and Celery-based asynchronous execution
- Restricted Python sandbox with AST validation and resource limits
- Dynamic webhook endpoints with optional secrets and API key authentication
- REST API for workflows, versions, nodes, and edges
- Real-time execution logs over WebSockets (Django Channels)
- Rate limiting for webhooks and API endpoints
- PostgreSQL, Redis, Celery, and Docker Compose support
- OpenAPI/Swagger documentation

## Architecture Overview

- `config/` — Django project package, settings, ASGI/WSGI, Celery app
- `apps/workflows/` — workflow domain models and admin
- `apps/executions/` — execution runner, Celery tasks, WebSocket consumers
- `apps/sandbox/` — AST validator and restricted Python executor
- `apps/api/` — REST API, webhooks, serializers, authentication, throttling
- `apps/core/` — shared models such as API keys

A workflow is versioned. Each `WorkflowVersion` contains nodes and edges. An `Execution` runs a published version in topological order and records `ExecutionLog` entries.

## Tech Stack

- Python 3.12+
- Django 6.x
- Django REST Framework
- Celery + Redis
- Django Channels + channels-redis
- PostgreSQL 16
- Daphne (ASGI)
- Docker & Docker Compose
- Ruff, pytest, pre-commit

## Quick Start

### Requirements

- Docker and Docker Compose (recommended)
- Or Python 3.12+, PostgreSQL 16, Redis 7

### With Docker Compose (recommended)

```bash
git clone https://github.com/KIRAZINA/flowforge.git
cd flowforge
cp .env.example .env
docker compose up --build
```

The web service runs migrations automatically and starts on `http://localhost:8000`.

### Without Docker

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements/development.txt
cp .env.example .env
# Start PostgreSQL and Redis locally, then:
python manage.py migrate
python manage.py runserver
```

In another terminal:

```bash
celery -A config worker -l info
```

## Running the Stack

With Docker Compose:

```bash
docker compose up --build        # start everything
docker compose up -d            # detached
docker compose logs -f web       # follow web logs
docker compose down             # stop
docker compose down -v          # stop and remove volumes
```

Optional services (profiles):

```bash
docker compose --profile flower up   # Celery Flower on :5555
docker compose --profile beat up     # Celery beat
```

## Example: Trigger a Workflow via Webhook

1. Create a workflow and published version through the API or admin.
2. Add a transform node with config:

```json
{"code": "result = {'message': 'Hello ' + data.get('name', 'world')}"}
```

3. Trigger it:

```bash
curl -X POST http://localhost:8000/hooks/my-workflow/ \
  -H "Content-Type: application/json" \
  -d '{"name": "FlowForge"}'
```

Response:

```json
{"execution_id": "...", "status": "pending"}
```

## API Documentation

Interactive Swagger UI is available at:

- `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`

## Project Structure

```text
FlowForge/
├── config/          # Django project package
├── apps/            # core, workflows, executions, sandbox, api
├── docker/          # Dockerfile
├── scripts/
├── tests/
├── requirements/
├── docker-compose.yml
├── manage.py
└── pyproject.toml
```

## Development

Run tests:

```bash
pytest -v
```

Lint and format:

```bash
ruff check .
ruff format --check .
```

Pre-commit hooks:

```bash
pre-commit install
```

## Security Notes

- User-provided Python code runs in a restricted sandbox with AST validation, a minimal builtin set, timeouts, and result size limits.
- API access can be protected with API keys (`Authorization: Api-Key <key>`).
- Webhooks support optional secrets and API keys.
- Rate limiting is applied to webhooks and API endpoints.
- The sandbox is best-effort and should not be treated as a complete isolation boundary.

## Roadmap

- Per-node Celery tasks and retries
- Conditional branching and loops
- HMAC webhook signatures
- OAuth / API key management UI
- Visual workflow editor
- Multi-tenant organizations

## License

MIT
