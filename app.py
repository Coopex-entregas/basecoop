import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timezone
from models import db, Usuario, Entrega
import pytz
import io
import pandas as pd
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sua_chave_secreta_aqui")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///entregas.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

ESPERA_FILE = 'motoboys_espera.json'

def carregar_espera():
    if os.path.exists(ESPERA_FILE):
        with open(ESPERA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def salvar_espera(lista):
    with open(ESPERA_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False)

def utc_to_brt(value):
    if not value:
        return ''
    utc = pytz.utc
    brt = pytz.timezone('America/Sao_Paulo')
    if value.tzinfo is None:
        value_utc = utc.localize(value)
    else:
        value_utc = value
    value_brt = value_utc.astimezone(brt)
    return value_brt.strftime('%d/%m/%Y %H:%M')

app.jinja_env.filters['utc_to_brt'] = utc_to_brt

def criar_usuario_padrao():
    if not Usuario.query.filter_by(nome="coopex").first():
        senha_hash = generate_password_hash("05062721")
        user = Usuario(nome="coopex", senha_hash=senha_hash, tipo="adm")
        db.session.add(user)
        db.session.commit()

@app.before_request
def proteger_rotas():
    rotas_protegidas = {
        "dashboard", "logout", "cadastrar_cooperado", "excluir_cooperado",
        "cadastrar_entrega", "editar_entrega", "excluir_entrega", "exportar_entregas",
        "motoboys_espera"
    }
    if request.endpoint in rotas_protegidas and "usuario_id" not in session:
        flash("Acesso não autorizado. Faça login para continuar.", "error")
        return redirect(url_for("login"))

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and check_password_hash(usuario.senha_hash, senha):
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome
            session["usuario_tipo"] = usuario.tipo
            flash("Login efetuado com sucesso!", "success")
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha incorretos.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    data_filtro_str = request.args.get('data_filtro')

    if data_filtro_str:
        try:
            data_filtro = datetime.strptime(data_filtro_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Data inválida para filtro.", "error")
            return redirect(url_for("dashboard"))
    else:
        data_filtro = date.today()

    inicio_dia = datetime.combine(data_filtro, time.min).replace(tzinfo=timezone.utc)
    fim_dia = datetime.combine(data_filtro, time.max).replace(tzinfo=timezone.utc)

    if session["usuario_tipo"] == "adm":
        cooperados = Usuario.query.filter_by(tipo="cooperado").all()
        entregas = Entrega.query.filter(
            Entrega.hora_pedido >= inicio_dia,
            Entrega.hora_pedido <= fim_dia
        ).order_by(Entrega.hora_pedido.desc()).all()

        # Estatísticas gerais:
        hoje = date.today()
        inicio_hoje = datetime.combine(hoje, time.min).replace(tzinfo=timezone.utc)
        fim_hoje = datetime.combine(hoje, time.max).replace(tzinfo=timezone.utc)

        inicio_mes = datetime.combine(date.today().replace(day=1), time.min).replace(tzinfo=timezone.utc)
        fim_mes = datetime.combine(date.today().replace(day=1), time.max).replace(tzinfo=timezone.utc)
        # para fim_mes vamos ajustar para o último dia do mês:
        from calendar import monthrange
        ano_atual = hoje.year
        mes_atual = hoje.month
        ultimo_dia_mes = monthrange(ano_atual, mes_atual)[1]
        fim_mes = datetime.combine(date(ano_atual, mes_atual, ultimo_dia_mes), time.max).replace(tzinfo=timezone.utc)

        inicio_ano = datetime(ano_atual, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        fim_ano = datetime(ano_atual, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        # Valor total do mês (pagos)
        valor_total_mes = db.session.query(func.coalesce(func.sum(Entrega.valor), 0)).filter(
            Entrega.hora_pedido >= inicio_mes,
            Entrega.hora_pedido <= fim_mes,
            Entrega.status_pagamento == 'pago'
        ).scalar()

        # Quantidade de entregas do dia
        entregas_dia = db.session.query(func.count(Entrega.id)).filter(
            Entrega.hora_pedido >= inicio_hoje,
            Entrega.hora_pedido <= fim_hoje
        ).scalar()

        # Quantidade de entregas do ano
        entregas_ano = db.session.query(func.count(Entrega.id)).filter(
            Entrega.hora_pedido >= inicio_ano,
            Entrega.hora_pedido <= fim_ano
        ).scalar()

        # Valor total feito por cada cooperado no mês
        valor_por_cooperado = db.session.query(
            Usuario.id,
            Usuario.nome,
            func.coalesce(func.sum(Entrega.valor), 0).label('total_valor')
        ).join(Entrega, Entrega.cooperado_id == Usuario.id).filter(
            Entrega.hora_pedido >= inicio_mes,
            Entrega.hora_pedido <= fim_mes,
            Entrega.status_pagamento == 'pago',
            Usuario.tipo == 'cooperado'
        ).group_by(Usuario.id).all()

        lista_espera = carregar_espera()
        return render_template("dashboard_admin.html",
                               cooperados=cooperados,
                               entregas=entregas,
                               data_filtro=data_filtro_str,
                               motoboys_espera=lista_espera,
                               valor_total_mes=valor_total_mes,
                               entregas_dia=entregas_dia,
                               entregas_ano=entregas_ano,
                               valor_por_cooperado=valor_por_cooperado)

    # Se for cooperado, mostra só as entregas dele no dia filtrado
    entregas = Entrega.query.filter(
        Entrega.cooperado_id == session["usuario_id"],
        Entrega.hora_pedido >= inicio_dia,
        Entrega.hora_pedido <= fim_dia
    ).order_by(Entrega.hora_pedido.desc()).all()
    return render_template("dashboard_cooperado.html", entregas=entregas)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logout realizado com sucesso.", "success")
    return redirect(url_for("login"))

@app.route("/cadastrar_cooperado", methods=["GET", "POST"])
def cadastrar_cooperado():
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito a administradores.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        if Usuario.query.filter_by(nome=nome).first():
            flash("Nome já cadastrado, escolha outro.", "error")
            return redirect(url_for("cadastrar_cooperado"))
        senha_hash = generate_password_hash(senha)
        novo = Usuario(nome=nome, senha_hash=senha_hash, tipo="cooperado")
        db.session.add(novo)
        db.session.commit()
        flash("Cooperado cadastrado com sucesso!", "success")
        return redirect(url_for("dashboard"))
    return render_template("cadastrar_cooperado.html")

@app.route("/excluir_cooperado/<int:cooperado_id>", methods=["POST"])
def excluir_cooperado(cooperado_id):
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito.", "error")
        return redirect(url_for("dashboard"))

    coop = Usuario.query.filter_by(id=cooperado_id, tipo="cooperado").first()
    if not coop:
        flash("Cooperado não encontrado.", "error")
        return redirect(url_for("dashboard"))
    Entrega.query.filter_by(cooperado_id=coop.id).delete()
    db.session.delete(coop)
    db.session.commit()
    flash(f"Cooperado '{coop.nome}' excluído com sucesso!", "success")
    return redirect(url_for("dashboard"))

@app.route("/cadastrar_entrega", methods=["GET", "POST"])
def cadastrar_entrega():
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito.", "error")
        return redirect(url_for("dashboard"))

    cooperados = Usuario.query.filter_by(tipo="cooperado").all()
    if request.method == "POST":
        descricao = request.form["cliente"]
        valor = request.form.get("valor", type=float)
        hora_str = request.form["hora_pedido"]
        coop_id = request.form.get("cooperado_id")
        try:
            hora_pedido = datetime.strptime(hora_str, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            flash("Formato de data/hora inválido.", "error")
            return redirect(url_for("cadastrar_entrega"))

        entrega = Entrega(
            descricao=descricao,
            valor=
