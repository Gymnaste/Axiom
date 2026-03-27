# Utiliser une image Python légère avec les dépendances Playwright
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copier les requirements et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium pour Playwright
RUN playwright install chromium

# Copier le reste du code
COPY . .

# Exposer le port (Koyeb utilise $PORT)
ENV PORT=8000
EXPOSE 8000

# Commande de démarrage
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
