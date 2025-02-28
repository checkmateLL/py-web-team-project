
FROM python:3.11-slim
WORKDIR /app

RUN pip install poetry

RUN apt-get update && apt-get install -y \
    libmagic1 libmagic-dev file \
    && rm -rf /var/lib/apt/lists/*


COPY pyproject.toml poetry.lock ./


RUN poetry config virtualenvs.create false && poetry install --no-root


COPY . .
EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]