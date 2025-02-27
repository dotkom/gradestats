FROM python:3.12-alpine

LABEL maintainer=dotkom@online.ntnu.no

COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

ENV NAME=gradestats
ENV DIR=/srv/app

RUN mkdir -p $DIR
WORKDIR $DIR

# Copy project files
COPY . $DIR

RUN mkdir -p static media
ENV DJANGO_SETTINGS_MODULE=$NAME.settings.prod
RUN uv run python manage.py collectstatic --noinput --clear

EXPOSE 8080
EXPOSE 8081

CMD ["sh", "docker-entrypoint.sh"]
