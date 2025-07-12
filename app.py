import os
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from pytz import timezone

app = Flask(__name__)
app.secret_key = 'coopex2024'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/banco.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

from models import Usuario, Entrega

# Filtro para converter UTC para horário de Brasília
@app.template_filter('utc_to_brt')
def utc_to_brt(utc_dt):
    if not utc_dt:
        return ''
    br_tz = timezone('America/Sao_Paulo')
    return utc_dt.astimezone(br_tz).strftime('%d/%m/%Y %H:%M')

# ---------------- ROTAS ---------------- #

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and usuario.senha == senha:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['usuario_tipo'] = usuario.tipo
            return redirect(url_for('dashboard'))
        else:
            flash('Nome ou senha inválidos')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    tipo = session['usuario_tipo']
    data_filtro = request.args.get('data_filtro')
    hoje = datetime.now(timezone('America/Sao_Paulo')).date()

    if data_filtro:
        try:
            data_obj = datetime.strptime(data_filtro, '%Y-%m-%d').date()
        except:
            data_obj = hoje
    else:
        data_obj = hoje

    if tipo == 'admin':
        entregas = Entrega.query.filter(
            db.func.date(Entrega.hora_pedido) == data_obj
        ).order_by(Entrega.hora_pedido.desc()).all()

        total_dia = len(entregas)
        total_entregas_ano = Entrega.query.filter(
            db.extract('year', Entrega.hora_pedido) == hoje.year
        ).count()

        total_valor_mes = db.session.query(db.func.sum(Entrega.valor)).filter(
            db.extract('month', Entrega.hora_pedido) == hoje.month,
            db.extract('year', Entrega.hora_pedido) == hoje.year
        ).scalar() or 0.0

        valores_por_cooperado = db.session.query(
            Usuario.nome, db.func.sum(Entrega.valor)
        ).join(Entrega).filter(
            db.extract('month', Entrega.hora_pedido) == hoje.month,
            db.extract('year', Entrega.hora_pedido) == hoje.year
        ).group_by(Usuario.nome).all()

        cooperados = Usuario.query.filter_by(tipo='cooperado').all()

        return render_template(
            'dashboard_admin.html',
            entregas=entregas,
            total_dia=total_dia,
            total_entregas_ano=total_entregas_ano,
            total_valor_mes=total_valor_mes,
            valores_por_cooperado=valores_por_cooperado,
            cooperados=cooperados,
            data_filtro=data_filtro,
            motoboys_espera=session.get('motoboys_espera', [])
        )
    else:
        usuario_id = session['usuario_id']
        entregas = Entrega.query.filter_by(cooperado_id=usuario_id).filter(
            db.func.date(Entrega.hora_pedido) == data_obj
        ).order_by(Entrega.hora_pedido.desc()).all()

        total_valor_mes = db.session.query(db.func.sum(Entrega.valor)).filter_by(cooperado_id=usuario_id).filter(
            db.extract('month', Entrega.hora_pedido) == hoje.month,
            db.extract('year', Entrega.hora_pedido) == hoje.year
        ).scalar() or 0.0

        total_valor_dia = db.session.query(db.func.sum(Entrega.valor)).filter_by(cooperado_id=usuario_id).filter(
            db.func.date(Entrega.hora_pedido) == hoje
        ).scalar() or 0.0

        return render_template(
            'dashboard_cooperado.html',
            entregas=entregas,
            total_valor_mes=total_valor_mes,
            total_valor_dia=total_valor_dia,
            data_filtro=data_filtro
        )

@app.route('/cadastrar_cooperado', methods=['GET', 'POST'])
def cadastrar_ou_editar_cooperado():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        if nome and senha:
            novo = Usuario(nome=nome, senha=senha, tipo='cooperado')
            db.session.add(novo)
            db.session.commit()
            flash('Cooperado cadastrado com sucesso!')
        return redirect(url_for('cadastrar_ou_editar_cooperado'))
    
    cooperados = Usuario.query.filter_by(tipo='cooperado').all()
    return render_template('cadastrar_cooperado.html', cooperados=cooperados)

@app.route('/excluir_cooperado/<int:cooperado_id>', methods=['POST'])
def excluir_cooperado(cooperado_id):
    cooperado = Usuario.query.get_or_404(cooperado_id)
    db.session.delete(cooperado)
    db.session.commit()
    flash(f"Cooperado {cooperado.nome} excluído com sucesso.")
    return redirect(url_for('cadastrar_ou_editar_cooperado'))

@app.route('/cadastrar_entrega', methods=['GET', 'POST'])
def cadastrar_entrega():
    cooperados = Usuario.query.filter_by(tipo='cooperado').all()
    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = float(request.form['valor'] or 0)
        hora_pedido = datetime.utcnow()
        hora_atribuida = datetime.utcnow()
        cooperado_id = int(request.form['cooperado_id'])
        status_pagamento = request.form['status_pagamento']
        status_entrega = request.form['status_entrega']

        nova = Entrega(
            descricao=descricao,
            valor=valor,
            hora_pedido=hora_pedido,
            hora_atribuida=hora_atribuida,
            cooperado_id=cooperado_id,
            status_pagamento=status_pagamento,
            status_entrega=status_entrega
        )
        db.session.add(nova)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('cadastrar_entrega.html', cooperados=cooperados)

@app.route('/editar_entrega/<int:entrega_id>', methods=['GET', 'POST'])
def editar_entrega(entrega_id):
    entrega = Entrega.query.get_or_404(entrega_id)
    cooperados = Usuario.query.filter_by(tipo='cooperado').all()
    if request.method == 'POST':
        entrega.descricao = request.form['descricao']
        entrega.valor = float(request.form['valor'] or 0)
        entrega.hora_atribuida = datetime.utcnow()
        entrega.cooperado_id = int(request.form['cooperado_id'])
        entrega.status_pagamento = request.form['status_pagamento']
        entrega.status_entrega = request.form['status_entrega']
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('editar_entrega.html', entrega=entrega, cooperados=cooperados)

@app.route('/excluir_entrega/<int:entrega_id>', methods=['POST'])
def excluir_entrega(entrega_id):
    entrega = Entrega.query.get_or_404(entrega_id)
    db.session.delete(entrega)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/exportar_entregas')
def exportar_entregas():
    from export_excel import exportar_entregas_para_excel
    return exportar_entregas_para_excel()

@app.route('/motoboys_espera', methods=['POST'])
def salvar_motoboys():
    data = request.get_json()
    session['motoboys_espera'] = data.get('motoboys', [])
    return jsonify({'status': 'ok'})

# ---------------- FIM ---------------- #

if __name__ == '__main__':
    app.run(debug=True)
