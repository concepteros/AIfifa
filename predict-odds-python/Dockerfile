FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

HEALTHCHECK --interval=5m --timeout=10s --retries=3 CMD predict-odds --help >/dev/null || exit 1

CMD ["predict-odds", "--help"]
