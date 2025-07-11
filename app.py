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
        lista_espera = carregar_espera()

        # Cálculo dos valores por cooperado no mês atual
        hoje = date.today()
        inicio_mes = datetime(hoje.year, hoje.month, 1, tzinfo=timezone.utc)
        fim_mes = datetime(hoje.year, hoje.month + 1 if hoje.month < 12 else 1, 1, tzinfo=timezone.utc) if hoje.month < 12 else datetime(hoje.year + 1, 1, 1, tzinfo=timezone.utc)

        valores_por_cooperado = []
        for c in cooperados:
            total = db.session.query(
                db.func.coalesce(db.func.sum(Entrega.valor), 0)
            ).filter(
                Entrega.cooperado_id == c.id,
                Entrega.hora_pedido >= inicio_mes,
                Entrega.hora_pedido < fim_mes
            ).scalar()
            valores_por_cooperado.append((c.nome, total))

        # Total ganho no mês
        total_valor_mes = db.session.query(
            db.func.coalesce(db.func.sum(Entrega.valor), 0)
        ).filter(
            Entrega.hora_pedido >= inicio_mes,
            Entrega.hora_pedido < fim_mes
        ).scalar()

        # Total entregas no dia filtrado
        total_dia = db.session.query(
            db.func.count(Entrega.id)
        ).filter(
            Entrega.hora_pedido >= inicio_dia,
            Entrega.hora_pedido <= fim_dia
        ).scalar()

        # Total entregas no ano atual
        inicio_ano = datetime(hoje.year, 1, 1, tzinfo=timezone.utc)
        fim_ano = datetime(hoje.year + 1, 1, 1, tzinfo=timezone.utc)
        total_entregas_ano = db.session.query(
            db.func.count(Entrega.id)
        ).filter(
            Entrega.hora_pedido >= inicio_ano,
            Entrega.hora_pedido < fim_ano
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

    # Para cooperados comuns, mostrar só suas entregas do dia filtrado
    entregas = Entrega.query.filter(
        Entrega.cooperado_id == session["usuario_id"],
        Entrega.hora_pedido >= inicio_dia,
        Entrega.hora_pedido <= fim_dia
    ).order_by(Entrega.hora_pedido.desc()).all()
    return render_template("dashboard_cooperado.html", entregas=entregas, data_filtro=data_filtro_str)

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
            valor=valor,
            hora_pedido=hora_pedido,
            status_pagamento="pendente",
            status_entrega="pendente",
            cooperado_id=int(coop_id) if coop_id else None,
            hora_atribuida=datetime.now(timezone.utc) if coop_id else None
        )
        db.session.add(entrega)
        db.session.commit()
        flash("Entrega cadastrada com sucesso!", "success")
        return redirect(url_for("dashboard"))

    return render_template("cadastrar_entrega.html", cooperados=cooperados)

@app.route("/editar_entrega/<int:entrega_id>", methods=["GET", "POST"])
def editar_entrega(entrega_id):
    entrega = Entrega.query.get_or_404(entrega_id)
    if (session["usuario_tipo"] == "cooperado" and entrega.cooperado_id != session["usuario_id"]):
        flash("Permissão negada.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        if session["usuario_tipo"] == "adm":
            entrega.descricao = request.form["descricao"]
            entrega.valor = request.form.get("valor", type=float)
            try:
                entrega.hora_pedido = datetime.strptime(
                    request.form["hora_pedido"], "%Y-%m-%dT%H:%M"
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                flash("Formato de data/hora inválido.", "error")
                return redirect(url_for("editar_entrega", entrega_id=entrega_id))
            coop_id = request.form.get("cooperado_id")
            entrega.cooperado_id = int(coop_id) if coop_id else None
            entrega.hora_atribuida = datetime.now(timezone.utc) if coop_id else None
            entrega.status_pagamento = request.form["status_pagamento"]
            entrega.status_entrega = request.form["status_entrega"]
        else:
            entrega.status_pagamento = request.form["status_pagamento"]
            entrega.status_entrega = request.form["status_entrega"]
        db.session.commit()
        flash("Entrega atualizada com sucesso!", "success")
        return redirect(url_for("dashboard"))

    cooperados = (Usuario.query.filter_by(tipo="cooperado").all()
                  if session["usuario_tipo"] == "adm" else [])
    return render_template("editar_entrega.html",
                           entrega=entrega,
                           cooperados=cooperados,
                           user_tipo=session["usuario_tipo"])

@app.route("/excluir_entrega/<int:entrega_id>", methods=["POST"])
def excluir_entrega(entrega_id):
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito.", "error")
        return redirect(url_for("dashboard"))
    entrega = Entrega.query.get_or_404(entrega_id)
    db.session.delete(entrega)
    db.session.commit()
    flash(f"Entrega #{entrega_id} excluída com sucesso!", "success")
    return redirect(url_for("dashboard"))

@app.route("/exportar_entregas")
def exportar_entregas():
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito.", "error")
        return redirect(url_for("dashboard"))
    entregas = Entrega.query.all()

    dados = []
    for e in entregas:
        dados.append({
            "Nome do Cliente": e.descricao,
            "Hora do Pedido": utc_to_brt(e.hora_pedido),
            "Hora Atribuída": utc_to_brt(e.hora_atribuida),
            "Valor (R$)": f"{e.valor:.2f}" if e.valor else "0.00",
            "Cooperado": e.cooperado.nome if e.cooperado else "Não atribuído",
            "Status Pagamento": e.status_pagamento.capitalize(),
            "Status Entrega": e.status_entrega.capitalize(),
        })

    df = pd.DataFrame(dados)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Entregas')

    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name='entregas.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route("/motoboys_espera", methods=["GET", "POST"])
def motoboys_espera():
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito a administradores.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        dados = request.get_json()
        lista = dados.get("motoboys", [])
        lista = [nome.strip() for nome in lista if nome.strip()]
        salvar_espera(lista)
        return {"status": "ok"}

    lista_atual = carregar_espera()
    return {"motoboys": lista_atual}

with app.app_context():
    db.create_all()
    criar_usuario_padrao()

if __name__ == "__main__":
    app.run(debug=True)
