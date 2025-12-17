# FROM python:3.11.4-slim-bullseye AS prod
# RUN apt-get update && apt-get install -y \
#   gcc \
#   && rm -rf /var/lib/apt/lists/*


# RUN pip install poetry==1.8.2

# # Configuring poetry
# RUN poetry config virtualenvs.create false
# RUN poetry config cache-dir /tmp/poetry_cache

# # Copying requirements of a project
# COPY pyproject.toml poetry.lock /app/src/
# WORKDIR /app/src

# # Installing requirements
# RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main
# # Removing gcc
# RUN apt-get purge -y \
#   gcc \
#   && rm -rf /var/lib/apt/lists/*

# # Copying actuall application
# COPY . /app/src/
# RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main

# CMD ["/usr/local/bin/python", "-m", "app"]

# FROM prod AS dev

# RUN --mount=type=cache,target=/tmp/poetry_cache poetry install



##########################################
# ------------ PROD IMAGE --------------
##########################################

FROM python:3.11.4-slim-bullseye AS prod

# Install build tools for dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.2

# Configure Poetry
RUN poetry config virtualenvs.create false
RUN poetry config cache-dir /tmp/poetry_cache

# Copy dependency files
COPY pyproject.toml poetry.lock /app/src/
WORKDIR /app/src

# Install main dependencies
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main

# Copy the main application
COPY . /app/src/

# Install again to include local modules
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main


##########################################
# -------- OPEN TELEMETRY STACK ---------
##########################################

RUN pip install \
    opentelemetry-api==1.38.0 \
    opentelemetry-sdk==1.38.0 \
    opentelemetry-exporter-otlp-proto-http==1.38.0 \
    opentelemetry-instrumentation==0.59b0 \
    opentelemetry-instrumentation-fastapi==0.59b0 \
    opentelemetry-instrumentation-logging==0.59b0 \
    opentelemetry-instrumentation-requests==0.59b0 \
    opentelemetry-distro==0.59b0 \
    && opentelemetry-bootstrap --action=install


##########################################
# -------- CLEANUP BUILD TOOLS ----------
##########################################

RUN apt-get purge -y \
    gcc \
    python3-dev \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*


##########################################
# -------- ENTRYPOINT + CMD -------------
##########################################

ENTRYPOINT ["opentelemetry-instrument"]

CMD ["uvicorn", "app.api.application:get_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]


##########################################
# --------------- DEV -------------------
##########################################

FROM prod AS dev

RUN --mount=type=cache,target=/tmp/poetry_cache poetry install