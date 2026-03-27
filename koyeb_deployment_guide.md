# Koyeb Deployment Guide

To deploy Axiom to Koyeb, follow these steps:

## 1. Environment Variables
In the Koyeb dashboard, add the following environment variables:
- `OPENAI_API_KEY`: Votre clé OpenAI
- `OPENAI_MODEL`: `gpt-4o-mini`
- `AI_ENABLED`: `true`
- `PORT`: `8000` (Koyeb injectera sa valeur, mais vous pouvez forcer 8000 si besoin)
- `DEBUG`: `false`
- `RISK_PROFILE`: `moderate`
- `SUPABASE_URL`: (Depuis votre Dashboard Supabase)
- `SUPABASE_KEY`: (Depuis votre Dashboard Supabase)

## 2. Deployment Settings
- **Service Type**: Web Service
- **Build Method**: **Docker** (Très important !)
- **Dockerfile path**: `backend/Dockerfile`
- **Docker context**: `backend/`
- **Run Command**: (Laissez vide, le Dockerfile s'en occupe)
- **Instance Type**: Nano (Free)

## 3. Playwright Note
Koyeb's free tier might struggle with Chromium. If you see "Out of Memory" errors in logs:
1. Let me know, I'll provide a way to disable the Twitter scraper.
2. Consider upgrading to a "Micro" instance ($5/mo) if you need reliable scraping.
