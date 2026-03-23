FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py x_bulk_block.py ./
COPY templates/ templates/
COPY static/ static/

# Run as a non-root user — least-privilege principle
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 7070

# Use gunicorn in production; works with both Render/Railway and local Docker
CMD gunicorn app:app \
    --bind 0.0.0.0:${PORT:-7070} \
    --workers 1 \
    --worker-class gevent \
    --worker-connections 50 \
    --timeout 120
