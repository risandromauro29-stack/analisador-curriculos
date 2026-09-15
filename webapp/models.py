from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=_agora)

    auditorias = db.relationship("Auditoria", backref="usuario", lazy="dynamic")

    def set_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def checar_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_active(self) -> bool:  # sobrescreve o UserMixin: usuário inativo não loga
        return self.ativo


class Auditoria(db.Model):
    __tablename__ = "auditorias"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=_agora, index=True)

    nome_arquivo = db.Column(db.String(255))
    obra = db.Column(db.String(255))
    empresa = db.Column(db.String(255))
    periodo_inicio = db.Column(db.String(20))
    periodo_fim = db.Column(db.String(20))
    total_colaboradores = db.Column(db.Integer, default=0)
    nao_conformidades_criticas = db.Column(db.Integer, default=0)
    nao_conformidades_atencao = db.Column(db.Integer, default=0)

    resumo_json = db.Column(db.Text)     # ponto_auditor.relatorio.resumo_auditoria(), serializado
    resumo_markdown = db.Column(db.Text)
    painel_html = db.Column(db.Text)     # o painel_ponto.html completo, servido sob demanda

    erro = db.Column(db.Text)  # preenchido quando o processamento falha (ex.: ErroDeLeitura)
