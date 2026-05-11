.PHONY: check test server shell migrate migrations admin static

check:
	python manage.py check

test:
	pytest

server:
	python manage.py runserver 127.0.0.1:8000

shell:
	python manage.py shell

migrate:
	python manage.py migrate

migrations:
	python manage.py makemigrations $(ARGS)

admin:
	python manage.py ensure_admin

static:
	python manage.py collectstatic --noinput
