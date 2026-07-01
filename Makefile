.DEFAULT_GOAL := help
.PHONY: help install run shell migrate migrations superuser test cov lint fmt typecheck \
        celery beat check up down logs

help:  ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install development dependencies.
	pip install -r requirements/development.txt

run:  ## Run the development server.
	python manage.py runserver 0.0.0.0:8000

shell:  ## Open the Django shell.
	python manage.py shell

migrations:  ## Create new migrations.
	python manage.py makemigrations

migrate:  ## Apply migrations.
	python manage.py migrate

superuser:  ## Create a superuser.
	python manage.py createsuperuser

check:  ## Run Django system checks.
	python manage.py check

test:  ## Run the test suite.
	pytest

cov:  ## Run tests with coverage report.
	pytest --cov --cov-report=term-missing

lint:  ## Lint the codebase.
	ruff check .

fmt:  ## Auto-format and fix lint issues.
	ruff check --fix .
	ruff format .

typecheck:  ## Run static type checking.
	mypy apps config

celery:  ## Run a Celery worker.
	celery -A config worker -l info

beat:  ## Run the Celery beat scheduler.
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

up:  ## Start the dev stack via docker compose.
	docker compose -f docker-compose.dev.yml up --build

down:  ## Stop the dev stack.
	docker compose -f docker-compose.dev.yml down

logs:  ## Tail dev stack logs.
	docker compose -f docker-compose.dev.yml logs -f
