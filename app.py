from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coopex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELOS
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # "admin" ou "cooperado"

class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200))
    valor = db.Column(db.Float)
    hora_pedido = db.Column(db.DateTime)
    hora_atribuida = db.Column(db.DateTime)
    cooperado_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    status_pagamento = db.Column(db.String(50))  # pago, pendente, etc.
    status_entrega = db.Column(db.String(50))    # entregue, pendente, etc.

# ROTAS
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['usuario_tipo'] = usuario.tipo
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    hoje = datetime.now().date()
    ano = datetime.now().year
    mes = datetime.now().month

    total_hoje = Entrega.query.filter(db.func.date(Entrega.hora_pedido) == hoje).count()
    total_ano = Entrega.query.filter(db.extract('year', Entrega.hora_pedido) == ano).count()

    entregas_mes = Entrega.query.filter(db.extract('month', Entrega.hora_pedido) == mes,
                                        db.extract('year', Entrega.hora_pedido) == ano).all()

    total_mes = sum(e.valor for e in entregas_mes if e.valor)

    ganhos_por_cooperado = {}
    for entrega in entregas_mes:
        if entrega.cooperado_id:
            usuario = Usuario.query.get(entrega.cooperado_id)
            if usuario:
                ganhos_por_cooperado.setdefault(usuario.nome, 0)
                ganhos_por_cooperado[usuario.nome] += entrega.valor or 0

    return render_template('dashboard_admin.html',
                           total_hoje=total_hoje,
                           total_ano=total_ano,
                           total_mes=total_mes,
                           ganhos_por_cooperado=ganhos_por_cooperado)

# Função opcional para criar admin padrão
def criar_usuario_padrao():
    if not Usuario.query.filter_by(email='admin@admin.com').first():
        admin = Usuario(nome='Admin', email='admin@admin.com', senha='admin', tipo='admin')
        db.session.add(admin)
        db.session.commit()

# Execução
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        criar_usuario_padrao()
    app.run(debug=True)
