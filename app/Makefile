.PHONY: install-dev-requirements fmt lint fmtl services \
	stop-services serve-django shell test reset

install-dev-requirements:
	@poetry install --with dev

fmt:
	@poetry run black --exclude __pycache__ --exclude migrations .
	@poetry run isort --skip migrations --skip __pycache__ .

lint:
	@poetry run flake8 --exclude '**/migrations/*' .

fmtl: fmt lint

services:
	@docker-compose up -d

stop-services:
	@docker-compose down

serve-django:
	@poetry run python manage.py runserver 0.0.0.0:8000

shell:
	@poetry run python manage.py shell_plus

celery:
	@poetry run celery -A backend worker --loglevel=DEBUG

test:
	@poetry run python manage.py test

reset:
	@poetry run python manage.py migrate
	@rm -rf media/*
	@mkdir media/profile_pics
	@cp fixtures/profile_pics/* media/profile_pics
	@cp fixtures/default.jpg media/
	@poetry run python manage.py loaddata filemanager/fixtures/FolderType.json
	@poetry run python manage.py loaddata fixtures/asset_types.json
	@poetry run python manage.py loaddata fixtures/suggested_fields.json
	@poetry run python manage.py loaddata fixtures/suggested_folders.json
	@poetry run python manage.py update_default_site

staging-release:
	@git tag staging-$$(date +%Y-%m-%dT%H%M)
	@git push --tags

prod-release:
	@git tag release-$$(date +%Y-%m-%dT%H%M)
	@git push --tags
