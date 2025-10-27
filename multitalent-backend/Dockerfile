# ---------- RUNTIME: Python + Gunicorn ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias de sistema (si necesitas psycopg2, etc. descomenta lo de abajo)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential libpq-dev gcc \
#   && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Gunicorn por defecto; los valores se pueden sobreescribir por compose
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--threads", "8", "--timeout", "60", "-b", "0.0.0.0:8000", "app.wsgi:app"]
