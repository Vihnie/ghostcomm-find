FROM python:3.12-slim
WORKDIR /service
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir . && useradd --create-home campus
COPY alembic.ini ./
COPY migrations ./migrations
RUN mkdir -p data/media && chown -R campus:campus /service
USER campus
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
