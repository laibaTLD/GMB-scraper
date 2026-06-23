FROM node:20-alpine AS frontend-build

WORKDIR /app/web-dashboard

COPY web-dashboard/package.json web-dashboard/package-lock.json ./
RUN npm ci

COPY web-dashboard/ ./

ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WDM_LOG_LEVEL=0 \
    STATIC_DIR=/app/static \
    API_HOST=0.0.0.0 \
    API_PORT=5178

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY backend/ ./backend/
COPY --from=frontend-build /app/web-dashboard/dist ./static/

RUN mkdir -p backend/downloads

EXPOSE 5178

CMD ["python", "app.py"]
