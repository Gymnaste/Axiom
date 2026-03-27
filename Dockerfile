# Dockerfile à la racine pour Koyeb
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Installation des dépendances (chemins relatifs à la racine du dépôt)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copie du code du backend
COPY backend/ .

# Configuration du port
ENV PORT=8000
EXPOSE 8000

# Lancement
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
