# FlowForge

FlowForge is an Event-Driven Workflow Automation Engine (an analog of n8n/Make) built with Django. It enables designing, executing, and monitoring automated workflows triggered by events, webhooks, schedules, and external integrations.

## Tech Stack

- Python 3.12+
- Django 6.x
- Django REST Framework
- Celery + Redis
- Django Channels (WebSockets / real-time)
- PostgreSQL
- Docker Compose

## Getting Started

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements/development.txt
cp .env.example .env

docker compose up -d db redis

python manage.py migrate
python manage.py runserver
```

## Project Layout

- `config/` - Django project package (settings, urls, asgi/wsgi, celery)
- `apps/` - Application modules (core, workflows, executions, sandbox, api)
- `docker/` - Dockerfiles (placeholder)
- `scripts/` - Utility scripts
- `tests/` - Test suite
