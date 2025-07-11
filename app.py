from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coopex.db'  # Ajuste para seu banco
app.config['SECRET_KEY'] = 'sua_chave_secreta'
db = SQLAlchemy(app)

# Models
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'adm' ou 'cooperado'

class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    hora_pedido = db.Column(db.DateTime, nullable=False)
    hora_atribuida = db.Column(db.DateTime)
    cooperado_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    status_pagamento = db.Column(db.String(50))
    status_entrega = db.Column(db.String(50))

# Login simples só para exemplo
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['usuario_tipo'] = usuario.tipo
            return redirect(url_for('dashboard'))
        flash('Usuário não encontrado.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    user_tipo = session.get('usuario_tipo')
    if user_tipo == 'adm':
        entregas = Entrega.query.order_by(Entrega.hora_pedido.desc()).all()
    else:
        entregas = Entrega.query.filter_by(cooperado_id=session.get('usuario_id')).order_by(Entrega.hora_pedido.desc()).all()
    return render_template('dashboard.html', entregas=entregas, user_tipo=user_tipo)

# Editar entrega
@app.route("/editar_entrega/<int:entrega_id>", methods=["GET", "POST"])
def editar_entrega(entrega_id):
    entrega = Entrega.query.get_or_404(entrega_id)
    if (session.get("usuario_tipo") == "cooperado" and entrega.cooperado_id != session.get("usuario_id")):
        flash("Permissão negada.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        if session.get("usuario_tipo") == "adm":
            entrega.descricao = request.form["descricao"]
            entrega.valor = request.form.get("valor", type=float)
            try:
                brt = pytz.timezone('America/Sao_Paulo')
                dt_local = datetime.strptime(request.form["hora_pedido"], "%Y-%m-%dT%H:%M")
                dt_localized = brt.localize(dt_local)
                entrega.hora_pedido = dt_localized.astimezone(pytz.utc)
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
                  if session.get("usuario_tipo") == "adm" else [])
    return render_template("editar_entrega.html",
                           entrega=entrega,
                           cooperados=cooperados,
                           user_tipo=session.get("usuario_tipo"))

# Rota para adicionar entrega (exemplo básico)
@app.route("/nova_entrega", methods=["GET", "POST"])
def nova_entrega():
    if 'usuario_tipo' not in session or session.get('usuario_tipo') != 'adm':
        flash("Acesso negado.", "error")
        return redirect(url_for('login'))
    if request.method == "POST":
        descricao = request.form["descricao"]
        valor = float(request.form["valor"])
        try:
            brt = pytz.timezone('America/Sao_Paulo')
            dt_local = datetime.strptime(request.form["hora_pedido"], "%Y-%m-%dT%H:%M")
            dt_localized = brt.localize(dt_local)
            hora_pedido_utc = dt_localized.astimezone(pytz.utc)
        except ValueError:
            flash("Formato de data/hora inválido.", "error")
            return redirect(url_for("nova_entrega"))
        entrega = Entrega(
            descricao=descricao,
            valor=valor,
            hora_pedido=hora_pedido_utc,
            status_pagamento="pendente",
            status_entrega="pendente"
        )
        db.session.add(entrega)
        db.session.commit()
        flash("Entrega adicionada com sucesso!", "success")
        return redirect(url_for("dashboard"))
    return render_template("nova_entrega.html")

if __name__ == "__main__":
    app.run(debug=True)
