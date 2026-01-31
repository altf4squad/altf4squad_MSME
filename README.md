# MSME Agentic AI System

A modern Flask-based dashboard for MSMEs focused on autonomous inventory decisions.

## Deployment on Render

To deploy this application on [Render](https://render.com), follow these steps:

1.  **Connect your Repository**: Link your GitHub/GitLab repository to Render.
2.  **Service Type**: Select **Web Service**.
3.  **Environment**: Choose **Python**.
4.  **Build Command**:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Start Command**:
    We use `gunicorn` for a production-ready, high-performance WSGI server.
    ```bash
    gunicorn app:app
    ```

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the development server:
   ```bash
   python app.py
   ```
3. Access at `http://127.0.0.1:5000`