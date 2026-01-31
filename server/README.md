# MSME Backend - Render Deployment Guide

To deploy this Flask application on Render:

1. **Create a New Web Service**: Connect your GitHub repository.
2. **Environment**: Select `Python 3`.
3. **Root Directory**: `server`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `gunicorn app:app`
6. **Environment Variables**:
   - `PORT`: 10000 (Render default) or leave as is.

## Keep-Alive
The project includes a GitHub Action to prevent the free tier instance from spinning down due to inactivity. See `.github/workflows/keep_alive.yml`.
