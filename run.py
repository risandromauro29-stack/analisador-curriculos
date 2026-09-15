"""Ponto de entrada da webapp. Local: `python run.py` (http://localhost:5000).
Produção: um servidor WSGI aponta pra `run:app` (ver Dockerfile/Procfile)."""
from webapp import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
