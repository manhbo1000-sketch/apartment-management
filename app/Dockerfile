FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt \
    && groupadd --gid 10001 apartment \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin apartment \
    && mkdir -p /app/logs \
    && chown -R 10001:10001 /app

COPY --chown=10001:10001 apartment ./apartment
COPY --chown=10001:10001 wsgi.py .
USER 10001:10001

EXPOSE 8000
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
