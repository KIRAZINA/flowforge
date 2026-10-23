.PHONY: up down test examples logs lint format

up:
	docker compose up --build

down:
	docker compose down

test:
	pytest -v

examples:
	python manage.py load_examples

logs:
	docker compose logs -f

lint:
	ruff check .

format:
	ruff format .
