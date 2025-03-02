FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

RUN apt-get update && apt-get install -y \
    libmagic1 libmagic-dev file \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml poetry.lock ./


RUN poetry config virtualenvs.create false && poetry install --no-root


COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
