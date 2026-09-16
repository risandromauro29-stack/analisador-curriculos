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

# --preload: carrega a app (e roda db.create_all()/bootstrap do admin) uma
# única vez no processo master antes de "forkar" os workers — sem isso, os
# workers corriam pra criar as tabelas do banco ao mesmo tempo e colidiam
# ("Worker failed to boot") no primeiro deploy.
# $PORT é injetada pelo Render/Railway/etc. — cai para 8000 fora desses ambientes
CMD ["sh", "-c", "gunicorn --preload --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 run:app"]
