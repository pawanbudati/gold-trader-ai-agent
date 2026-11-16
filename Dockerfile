FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source, data, tests, and entrypoints
COPY src/ /app/src/
COPY data/ /app/data/
COPY tests/ /app/tests/
COPY main.py /app/main.py
COPY listen.py* /app/
COPY service_account.json* /app/

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --retries=3 CMD python -c "import urllib.request; resp = urllib.request.urlopen('https://api.binance.com/api/v3/ping'); exit(0 if resp.status == 200 else 1)"

CMD ["python", "main.py"]
