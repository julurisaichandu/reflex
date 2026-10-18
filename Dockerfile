# MCP server image for Manufact. Sandbox runs go to SANDBOX_URL (server/runner.py on a Docker host).
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY server ./server
COPY README_AGENTS.md ./
ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1 MCP_USE_ANONYMIZED_TELEMETRY=false
EXPOSE 8000
USER 10001
CMD ["/app/.venv/bin/python", "-m", "server.main"]
