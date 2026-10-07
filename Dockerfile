FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir uv==0.11.28

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data

RUN uv sync --locked \
    && uv pip install --python .venv/bin/python --no-cache "psycopg[binary]>=3.2,<4"

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["factorydb-api"]
