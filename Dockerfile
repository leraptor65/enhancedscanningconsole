# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/vite.config.js ./
RUN npm install

COPY frontend/ ./
RUN npm run build


# Stage 2: Final lightweight python backend
FROM python:3.11-slim
WORKDIR /app

# Install evdev dependencies
RUN apt-get update && apt-get install -y gcc libevdev2 build-essential && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for SQLite database mapping
RUN mkdir -p /app/backend/data

COPY backend/ /app/backend/

# Copy compiled React frontend into backend static folder
COPY --from=frontend-builder /app/frontend/dist /app/backend/static

WORKDIR /app/backend

EXPOSE 8000

ENV DATABASE_URL=sqlite:///./data/scans.db

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
