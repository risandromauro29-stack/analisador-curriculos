"""Testes de ponta a ponta da webapp via test client do Flask (sem subir
servidor de verdade): login obrigatório, fluxo de upload + auditoria, e
gestão de usuários restrita a administrador."""
from pathlib import Path

import pytest

from webapp import create_app
from webapp.extensions import db
from webapp.models import Auditoria, Usuario

FIXTURES = Path(__file__).parent / "fixtures"
PDF_AMOSTRA = FIXTURES / "cartao_ponto_amostra.pdf"


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "teste",
    })
    with app.app_context():
        admin = Usuario(nome="Admin", email="admin@teste.com", is_admin=True, ativo=True)
        admin.set_senha("senha-forte-123")
        db.session.add(admin)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email="admin@teste.com", senha="senha-forte-123"):
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=True)


def test_pagina_de_auditorias_exige_login(client):
    resp = client.get("/auditorias/", follow_redirects=True)
    assert b"Entrar" in resp.data


def test_login_com_credenciais_invalidas(client):
    resp = login(client, senha="errada")
    assert "inválidos".encode("utf-8") in resp.data


def test_login_e_logout(client):
    resp = login(client)
    assert resp.status_code == 200
    assert "Auditorias".encode() in resp.data

    resp = client.get("/logout", follow_redirects=True)
    assert b"Entrar" in resp.data


def test_fluxo_completo_de_auditoria(app, client):
    login(client)
    with open(PDF_AMOSTRA, "rb") as f:
        resp = client.post(
            "/auditorias/nova",
            data={"pdf": (f, "cartao_ponto_amostra.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200
    assert b"processada com sucesso" in resp.data

    with app.app_context():
        auditorias = Auditoria.query.all()
        assert len(auditorias) == 1
        auditoria = auditorias[0]
        assert auditoria.total_colaboradores == 6
        assert auditoria.nao_conformidades_criticas > 0
        assert auditoria.painel_html and "const DB=" in auditoria.painel_html

    resp_painel = client.get(f"/auditorias/{auditoria.id}/painel")
    assert resp_painel.status_code == 200
    assert resp_painel.mimetype == "text/html"

    resp_resumo = client.get(f"/auditorias/{auditoria.id}/resumo.md")
    assert resp_resumo.status_code == 200
    assert b"Auditoria de ponto" in resp_resumo.data


def test_outro_usuario_nao_ve_auditoria_alheia(app, client):
    with app.app_context():
        outro = Usuario(nome="Outro", email="outro@teste.com", is_admin=False, ativo=True)
        outro.set_senha("outra-senha-123")
        db.session.add(outro)
        db.session.commit()

    login(client)
    with open(PDF_AMOSTRA, "rb") as f:
        client.post(
            "/auditorias/nova", data={"pdf": (f, "amostra.pdf")},
            content_type="multipart/form-data", follow_redirects=True,
        )
    client.get("/logout")

    login(client, email="outro@teste.com", senha="outra-senha-123")
    resp = client.get("/auditorias/1")
    assert resp.status_code == 403


def test_gestao_de_usuarios_restrita_a_admin(app, client):
    with app.app_context():
        comum = Usuario(nome="Comum", email="comum@teste.com", is_admin=False, ativo=True)
        comum.set_senha("senha-comum-123")
        db.session.add(comum)
        db.session.commit()

    login(client, email="comum@teste.com", senha="senha-comum-123")
    assert client.get("/admin/usuarios").status_code == 403

    client.get("/logout")
    login(client)  # volta como admin
    resp = client.post(
        "/admin/usuarios", data={"nome": "Novo Usuário", "email": "novo@teste.com"},
        follow_redirects=True,
    )
    assert b"criado" in resp.data
    with app.app_context():
        assert Usuario.query.filter_by(email="novo@teste.com").first() is not None


def test_usuario_desativado_nao_loga(app, client):
    with app.app_context():
        inativo = Usuario(nome="Inativo", email="inativo@teste.com", is_admin=False, ativo=False)
        inativo.set_senha("senha-inativo-123")
        db.session.add(inativo)
        db.session.commit()

    resp = login(client, email="inativo@teste.com", senha="senha-inativo-123")
    assert b"desativado" in resp.data
