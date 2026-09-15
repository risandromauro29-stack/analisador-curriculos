import functools
import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Usuario

bp = Blueprint("admin", __name__, url_prefix="/admin")


def somente_admin(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


@bp.route("/usuarios", methods=["GET", "POST"])
@login_required
@somente_admin
def usuarios():
    senha_gerada = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        is_admin = bool(request.form.get("is_admin"))

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "erro")
        elif Usuario.query.filter_by(email=email).first():
            flash(f"Já existe um usuário com o e-mail {email}.", "erro")
        else:
            senha_gerada = secrets.token_urlsafe(9)
            novo = Usuario(nome=nome, email=email, is_admin=is_admin, ativo=True)
            novo.set_senha(senha_gerada)
            db.session.add(novo)
            db.session.commit()
            flash(f"Usuário {nome} criado. Envie a senha abaixo por um canal seguro — ela não será mostrada de novo.", "ok")

    lista = Usuario.query.order_by(Usuario.criado_em.desc()).all()
    return render_template("admin_usuarios.html", usuarios=lista, senha_gerada=senha_gerada)


@bp.route("/usuarios/<int:usuario_id>/alternar-ativo", methods=["POST"])
@login_required
@somente_admin
def alternar_ativo(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.id == current_user.id:
        flash("Você não pode desativar a própria conta.", "erro")
    else:
        usuario.ativo = not usuario.ativo
        db.session.commit()
        flash(f"Usuário {usuario.nome} {'ativado' if usuario.ativo else 'desativado'}.", "ok")
    return redirect(url_for("admin.usuarios"))


@bp.route("/usuarios/<int:usuario_id>/redefinir-senha", methods=["POST"])
@login_required
@somente_admin
def redefinir_senha(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    nova_senha = secrets.token_urlsafe(9)
    usuario.set_senha(nova_senha)
    db.session.commit()
    flash(f"Nova senha de {usuario.nome}: {nova_senha} — anote agora, não será mostrada de novo.", "ok")
    return redirect(url_for("admin.usuarios"))
