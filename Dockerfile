FROM node:22-bookworm-slim AS client
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY web/build.mjs web/client.js web/session.js web/index.html web/styles.css ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 \
    VIAL_API_STORAGE=/data/archives VIAL_BACKUP_DIR=/data/backups
WORKDIR /app
COPY requirements-server.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-server.lock \
    && groupadd --gid 10001 vial && useradd --uid 10001 --gid vial --no-create-home vial \
    && mkdir -p /data/archives && chown -R vial:vial /data
COPY src ./src
COPY run_server.py ./
COPY scripts/backup_central.py scripts/retain_archives.py ./scripts/
COPY deploy/prod-ca-2021.crt ./deploy/prod-ca-2021.crt
COPY --from=client /build/web/dist ./web/dist
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health',timeout=8)"
CMD ["python", "run_server.py"]
