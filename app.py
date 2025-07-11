import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timezone
from models import db, Usuario, Entrega
import pytz
import io
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sua_chave_secreta_aqui")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///entregas.db")
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

    brt = pytz.timezone('America/Sao_Paulo')
    inicio_dia = brt.localize(datetime.combine(data_filtro, time.min))
    fim_dia = brt.localize(datetime.combine(data_filtro, time.max))

    inicio_dia_utc = inicio_dia.astimezone(pytz.utc)
    fim_dia_utc = fim_dia.astimezone(pytz.utc)

    if session["usuario_tipo"] == "adm":
        cooperados = Usuario.query.filter_by(tipo="cooperado").all()
        entregas = Entrega.query.filter(
            Entrega.hora_pedido >= inicio_dia_utc,
            Entrega.hora_pedido <= fim_dia_utc
        ).order_by(Entrega.hora_pedido.desc()).all()
        lista_espera = carregar_espera()

        hoje = date.today()
        inicio_mes = brt.localize(datetime(hoje.year, hoje.month, 1))
        if hoje.month == 12:
            inicio_mes_prox = brt.localize(datetime(hoje.year + 1, 1, 1))
        else:
            inicio_mes_prox = brt.localize(datetime(hoje.year, hoje.month + 1, 1))
        inicio_mes_utc = inicio_mes.astimezone(pytz.utc)
        inicio_mes_prox_utc = inicio_mes_prox.astimezone(pytz.utc)

        valores_por_cooperado = []
        for c in cooperados:
            total = db.session.query(
                db.func.coalesce(db.func.sum(Entrega.valor), 0)
            ).filter(
                Entrega.cooperado_id == c.id,
                Entrega.hora_pedido >= inicio_mes_utc,
                Entrega.hora_pedido < inicio_mes_prox_utc
            ).scalar()
            valores_por_cooperado.append((c.nome, total))

        total_valor_mes = db.session.query(
            db.func.coalesce(db.func.sum(Entrega.valor), 0)
        ).filter(
            Entrega.hora_pedido >= inicio_mes_utc,
            Entrega.hora_pedido < inicio_mes_prox_utc
        ).scalar()

        inicio_ano = brt.localize(datetime(hoje.year, 1, 1))
        inicio_ano_prox = brt.localize(datetime(hoje.year + 1, 1, 1))
        inicio_ano_utc = inicio_ano.astimezone(pytz.utc)
        inicio_ano_prox_utc = inicio_ano_prox.astimezone(pytz.utc)

        total_dia = db.session.query(
            db.func.count(Entrega.id)
        ).filter(
            Entrega.hora_pedido >= inicio_dia_utc,
            Entrega.hora_pedido <= fim_dia_utc
        ).scalar()

        total_entregas_ano = db.session.query(
            db.func.count(Entrega.id)
        ).filter(
            Entrega.hora_pedido >= inicio_ano_utc,
            Entrega.hora_pedido < inicio_ano_prox_utc
        ).scalar()

        return render_template(
            "dashboard_admin.html",
            cooperados=cooperados,
            entregas=entregas,
            data_filtro=data_filtro_str,
            motoboys_espera=lista_espera,
            valores_por_cooperado=valores_por_cooperado,
            total_valor_mes=total_valor_mes,
            total_dia=total_dia,
            total_entregas_ano=total_entregas_ano
        )

    entregas = Entrega.query.filter(
        Entrega.cooperado_id == session["usuario_id"],
        Entrega.hora_pedido >= inicio_dia_utc,
        Entrega.hora_pedido <= fim_dia_utc
    ).order_by(Entrega.hora_pedido.desc()).all()
    return render_template("dashboard_cooperado.html", entregas=entregas, data_filtro=data_filtro_str)

# Outras rotas permanecem inalteradas
# ...

with app.app_context():
    db.create_all()
    criar_usuario_padrao()

if __name__ == "__main__":
    app.run(debug