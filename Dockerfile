FROM python:3.12

RUN pip install psycopg2
RUN pip install gunicorn
RUN apt-get update && apt-get install -y supervisor curl
RUN apt-get install libmagic1

# Install poetry:
RUN pip install poetry

RUN cd ~
RUN mkdir "app"
WORKDIR /app

# Copy in the config files:
COPY ./pyproject.toml /app/pyproject.toml
COPY ./poetry.lock /app/poetry.lock
COPY ./__version__.py /app/__version__.py
COPY ./README.md /app/README.md

# Copy the package files
COPY ./doorbeen /app/doorbeen

# Copy the local.env file and rename it to .env
COPY ./local.env /app/.env

# Load environment variables from .env file
ENV $(cat /app/.env | xargs)

# Install the package and dependencies:
RUN poetry config virtualenvs.create false && poetry install --no-root
RUN poetry install

RUN export DOCKER_DEFAULT_PLATFORM=linux/amd64

EXPOSE 9001

# Configure healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:9001/health || exit 1

# Run API Server with proper logging enabled
ENTRYPOINT ["gunicorn", "-w", "4", \
            "-k", "uvicorn.workers.UvicornWorker", \
            "-b", "0.0.0.0:9001", \
            "--keep-alive", "360", \
            "--timeout", "360", \
            "--access-logfile", "-", \
            "--error-logfile", "-", \
            "--access-logformat", "'%(h)s %(l)s %(u)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\"'", \
            "--log-level", "debug", \
            "--logger-class", "gunicorn.glogging.Logger", \
            "doorbeen.api.main:app"]
