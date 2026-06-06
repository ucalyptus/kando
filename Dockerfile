FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY kando ./kando
COPY kits ./kits
COPY mcp ./mcp

CMD ["python", "-m", "kando.cli.main", "status", "demo"]
