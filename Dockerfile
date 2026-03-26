FROM python:3.11-slim-bookworm

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies and project
# Using --system to install into system python, which is fine for docker container
RUN uv pip install --system .

ENTRYPOINT ["ko2ka"]
