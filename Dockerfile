# ==============================================================
# FIN-SYS OS — Backend Dockerfile
# FastAPI + Gunicorn (solo backend, sin frontend)
# ==============================================================

FROM python:3.12-slim

# Dependencias del sistema para psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend
COPY server.py .
COPY fin_sys_core/ ./fin_sys_core/
COPY routers/ ./routers/
COPY kernel/ ./kernel/
COPY shared/ ./shared/

# Crear directorio de uploads
RUN mkdir -p uploads

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["gunicorn", "server:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-"]
