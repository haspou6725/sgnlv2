FROM python:3.10-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 sgnl && \
    chown -R sgnl:sgnl /app && \
    mkdir -p /app/state && \
    chown -R sgnl:sgnl /app/state

USER sgnl

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sqlite3, os; \
    db = os.path.join('/app/state', 'data.db') if os.path.exists('/app/state') else 'data.db'; \
    conn = sqlite3.connect(db, timeout=5); \
    conn.execute('SELECT 1'); \
    conn.close(); \
    print('ok')"

CMD ["python", "main.py"]
