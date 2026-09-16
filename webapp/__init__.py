import os

from flask import Flask

from .extensions import csrf, db, login_manager


def create_app(config_extra: dict | None = None) -> Flask:
    app = Flask(__name__)

    db_url = os.environ.get("DATABASE_URL", "sqlite:///ponto_auditor.db")
    # Render/Railway às vezes fornecem "postgres://" — SQLAlchemy 2.x exige "postgresql://"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao"),
        SQLALCHEMY_DATABASE_URI=db_url,
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,  # 25 MB por upload
    )
    if config_extra:
        app.config.update(config_extra)

    # pool pequeno de propósito: 1 worker gunicorn não precisa de mais que
    # isso, e cada conexão Postgres consome memória — relevante no plano
    # free do Render (512MB no total). pool_size/max_overflow são
    # exclusivos do QueuePool (Postgres/MySQL/...) — SQLite (usado nos
    # testes e no fallback local) usa StaticPool e não aceita esses args.
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True, "pool_size": 3, "max_overflow": 2,
        }

    if app.config["SECRET_KEY"] == "troque-esta-chave-em-producao" and not app.debug:
        app.logger.warning(
            "SECRET_KEY não definida via variável de ambiente — as sessões de login "
            "serão invalidadas a cada reinício da aplicação. Defina SECRET_KEY em produção."
        )

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401 — registra os modelos no SQLAlchemy

    @login_manager.user_loader
    def carregar_usuario(usuario_id):
        return db.session.get(models.Usuario, int(usuario_id))

    from .admin import bp as admin_bp
    from .auditorias import bp as auditorias_bp
    from .auth import bp as auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(auditorias_bp, url_prefix="/auditorias")
    app.register_blueprint(admin_bp)

    from flask import redirect, url_for

    @app.route("/")
    def raiz():
        return redirect(url_for("auditorias.listar"))

    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:
            # defesa extra além do --preload do gunicorn (ver Dockerfile/Procfile):
            # se por algum motivo dois processos ainda colidirem criando as
            # tabelas ao mesmo tempo, não derruba o worker — as tabelas já
            # existirão quando a app começar a atender requisições.
            app.logger.warning(f"db.create_all() falhou (pode ser corrida entre processos, ignorando): {exc}")
            db.session.rollback()
        _bootstrap_admin(app)

    return app


def _bootstrap_admin(app: Flask) -> None:
    """Cria o primeiro administrador a partir de variáveis de ambiente, se
    ainda não existir nenhum usuário — necessário porque PaaS gratuitos
    normalmente não dão acesso a shell para rodar um comando manual."""
    from .models import Usuario

    if Usuario.query.first() is not None:
        return

    email = os.environ.get("ADMIN_EMAIL")
    senha = os.environ.get("ADMIN_SENHA")
    if not email or not senha:
        app.logger.warning(
            "Nenhum usuário cadastrado e ADMIN_EMAIL/ADMIN_SENHA não definidos — "
            "ninguém conseguirá fazer login. Defina essas variáveis de ambiente."
        )
        return

    admin = Usuario(nome=os.environ.get("ADMIN_NOME", "Administrador"), email=email.strip().lower(), is_admin=True, ativo=True)
    admin.set_senha(senha)
    db.session.add(admin)
    db.session.commit()
    app.logger.info(f"Administrador inicial criado: {email}")
