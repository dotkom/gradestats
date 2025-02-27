#!/usr/bin/env sh
uv run python manage.py migrate

DJANGO_SETTINGS_MODULE=gradestats.settings.prod exec uv run -- daphne --port=8081 --bind 0.0.0.0 gradestats.asgi:application
