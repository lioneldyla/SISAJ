FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-render.lock ./
COPY docker-wheels/ /opt/wheels/
ARG SISA_OFFLINE_BUILD=0
RUN if [ "$SISA_OFFLINE_BUILD" = "1" ]; then pip install --require-hashes --no-cache-dir --no-index --find-links=/opt/wheels -r requirements-render.lock; else pip install --require-hashes --no-cache-dir -r requirements-render.lock; fi && rm -rf /opt/wheels && useradd --create-home --uid 10001 sisa
COPY app ./app
COPY examples ./examples
COPY scripts/load_test_package.py ./scripts/load_test_package.py
RUN mkdir -p /app/data /app/backups && chown -R sisa:sisa /app
USER sisa
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips='*'"]
