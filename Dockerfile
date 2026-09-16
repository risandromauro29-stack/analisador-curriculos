FROM python:3.11-slim

WORKDIR /app

# libs nativas exigidas por pdfplumber/cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 1 worker: no plano free (0.1 CPU) mais de um worker não ajuda em nada, e
# evita dois problemas de uma vez — a corrida de dois processos criando as
# tabelas do banco ao mesmo tempo, e o problema (conhecido) de conexão
# Postgres corrompida quando --preload é usado com múltiplos workers (a
# conexão do processo master fica compartilhada entre os forks).
# $PORT é injetada pelo Render/Railway/etc. — cai para 8000 fora desses ambientes
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 120 run:app"]
