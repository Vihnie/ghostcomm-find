FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

FROM python:3.12-slim
WORKDIR /service
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir . && useradd --create-home campus
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY --from=frontend /frontend/dist ./frontend
ENV FRONTEND_DIR=/service/frontend
RUN mkdir -p data/media && chown -R campus:campus /service
USER campus
EXPOSE 8000
CMD ["sh", "-c", "python -m app.init_db && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
