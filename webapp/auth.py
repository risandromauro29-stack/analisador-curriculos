from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auditorias.listar"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not usuario.checar_senha(senha):
            flash("E-mail ou senha inválidos.", "erro")
        elif not usuario.ativo:
            flash("Este usuário está desativado. Fale com um administrador.", "erro")
        else:
            login_user(usuario, remember=True)
            proximo = request.args.get("next")
            return redirect(proximo or url_for("auditorias.listar"))

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/minha-conta", methods=["GET", "POST"])
@login_required
def minha_conta():
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmacao = request.form.get("confirmacao", "")

        if not current_user.checar_senha(senha_atual):
            flash("Senha atual incorreta.", "erro")
        elif len(nova_senha) < 8:
            flash("A nova senha precisa ter pelo menos 8 caracteres.", "erro")
        elif nova_senha != confirmacao:
            flash("A confirmação não bate com a nova senha.", "erro")
        else:
            from .extensions import db

            current_user.set_senha(nova_senha)
            db.session.commit()
            flash("Senha alterada com sucesso.", "ok")
            return redirect(url_for("auditorias.listar"))

    return render_template("minha_conta.html")
