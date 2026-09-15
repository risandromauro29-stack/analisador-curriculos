import json
import tempfile
from pathlib import Path

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ponto_auditor.calculos import aplicar_calculos
from ponto_auditor.efetivo import aplicar_efetivo, carregar_efetivo
from ponto_auditor.parser_pdf import ErroDeLeitura, parse_espelho_pdf
from ponto_auditor.relatorio import aplicar_regras, renderizar_painel_html, resumo_auditoria, resumo_markdown

from .extensions import db
from .models import Auditoria

bp = Blueprint("auditorias", __name__)

EXTENSOES_PDF = {".pdf"}
EXTENSOES_PLANILHA = {".xlsx", ".xlsm"}


@bp.route("/")
@login_required
def listar():
    query = Auditoria.query.order_by(Auditoria.criado_em.desc())
    if not current_user.is_admin:
        query = query.filter_by(usuario_id=current_user.id)
    auditorias = query.limit(100).all()
    return render_template("lista_auditorias.html", auditorias=auditorias)


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if request.method == "POST":
        arquivo_pdf = request.files.get("pdf")
        arquivo_efetivo = request.files.get("efetivo")

        if not arquivo_pdf or not arquivo_pdf.filename:
            flash("Selecione o PDF do Cartão Ponto.", "erro")
            return render_template("nova_auditoria.html")

        nome_pdf = secure_filename(arquivo_pdf.filename)
        if Path(nome_pdf).suffix.lower() not in EXTENSOES_PDF:
            flash("O arquivo do espelho de ponto precisa ser um PDF.", "erro")
            return render_template("nova_auditoria.html")

        if arquivo_efetivo and arquivo_efetivo.filename:
            nome_efetivo = secure_filename(arquivo_efetivo.filename)
            if Path(nome_efetivo).suffix.lower() not in EXTENSOES_PLANILHA:
                flash("A planilha de efetivo precisa ser .xlsx.", "erro")
                return render_template("nova_auditoria.html")
        else:
            nome_efetivo = None

        with tempfile.TemporaryDirectory() as tmp:
            caminho_pdf = Path(tmp) / nome_pdf
            arquivo_pdf.save(caminho_pdf)

            try:
                periodo = parse_espelho_pdf(str(caminho_pdf))
            except ErroDeLeitura as e:
                _registrar_erro(nome_pdf, str(e))
                flash(f"Não consegui ler esse PDF: {e}", "erro")
                return render_template("nova_auditoria.html")

            if nome_efetivo:
                caminho_efetivo = Path(tmp) / nome_efetivo
                arquivo_efetivo.save(caminho_efetivo)
                registros = carregar_efetivo(str(caminho_efetivo))
                periodo.sem_cadastro = aplicar_efetivo(periodo.colaboradores, registros)

            for colaborador in periodo.colaboradores:
                aplicar_calculos(colaborador)
            aplicar_regras(periodo)

            resumo = resumo_auditoria(periodo)
            auditoria = Auditoria(
                usuario_id=current_user.id,
                nome_arquivo=nome_pdf,
                obra=periodo.obra,
                empresa=periodo.empresa,
                periodo_inicio=periodo.inicio,
                periodo_fim=periodo.fim,
                total_colaboradores=resumo["colaboradores"],
                nao_conformidades_criticas=resumo["nao_conformidades_criticas"],
                nao_conformidades_atencao=resumo["nao_conformidades_atencao"],
                resumo_json=json.dumps(resumo, ensure_ascii=False),
                resumo_markdown=resumo_markdown(periodo),
                painel_html=renderizar_painel_html(periodo),
            )
            db.session.add(auditoria)
            db.session.commit()

        flash("Auditoria processada com sucesso.", "ok")
        return redirect(url_for("auditorias.ver", auditoria_id=auditoria.id))

    return render_template("nova_auditoria.html")


def _registrar_erro(nome_arquivo: str, mensagem: str) -> None:
    db.session.add(Auditoria(usuario_id=current_user.id, nome_arquivo=nome_arquivo, erro=mensagem))
    db.session.commit()


def _buscar_auditoria_do_usuario(auditoria_id: int) -> Auditoria:
    auditoria = Auditoria.query.get_or_404(auditoria_id)
    if not current_user.is_admin and auditoria.usuario_id != current_user.id:
        abort(403)
    return auditoria


@bp.route("/<int:auditoria_id>")
@login_required
def ver(auditoria_id):
    auditoria = _buscar_auditoria_do_usuario(auditoria_id)
    resumo = json.loads(auditoria.resumo_json) if auditoria.resumo_json else None
    return render_template("ver_auditoria.html", auditoria=auditoria, resumo=resumo)


@bp.route("/<int:auditoria_id>/painel")
@login_required
def painel(auditoria_id):
    auditoria = _buscar_auditoria_do_usuario(auditoria_id)
    if not auditoria.painel_html:
        abort(404)
    return Response(auditoria.painel_html, mimetype="text/html")


@bp.route("/<int:auditoria_id>/resumo.md")
@login_required
def resumo_md(auditoria_id):
    auditoria = _buscar_auditoria_do_usuario(auditoria_id)
    if not auditoria.resumo_markdown:
        abort(404)
    return Response(
        auditoria.resumo_markdown, mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=resumo_auditoria_{auditoria.id}.md"},
    )


@bp.route("/<int:auditoria_id>/excluir", methods=["POST"])
@login_required
def excluir(auditoria_id):
    auditoria = _buscar_auditoria_do_usuario(auditoria_id)
    db.session.delete(auditoria)
    db.session.commit()
    flash("Auditoria excluída.", "info")
    return redirect(url_for("auditorias.listar"))
