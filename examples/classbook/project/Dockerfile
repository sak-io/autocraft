FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY classbook ./classbook
RUN useradd --system --create-home app && mkdir -p /data && chown app /data
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'),timeout=2)"
# One worker only (SQLite, ADR-0002). --no-proxy-headers: only client_ip() may read X-Forwarded-For (T-18). Config comes from environment variables only.
CMD ["sh", "-c", "exec uvicorn --factory classbook.app:create_app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log --no-proxy-headers"]
