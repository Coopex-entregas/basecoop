from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = "segredo"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///entregas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    senha_hash = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # adm ou coop

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

class Entrega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100), nullable=False)
    bairro = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    cooperado_nome = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="pendente")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and usuario.verificar_senha(senha):
            session["usuario"] = usuario.nome
            session["tipo"] = usuario.tipo
            return redirect("/painel")
        else:
            return render_template("login.html", erro="Usuário ou senha inválido.")
    return render_template("login.html")

@app.route("/painel")
def painel():
    if "usuario" not in session:
        return redirect("/")
    usuario = session["usuario"]
    tipo = session["tipo"]
    if tipo == "adm":
        entregas = Entrega.query.all()
        cooperados = Usuario.query.filter_by(tipo="coop").all()
        return render_template("painel_adm.html", usuario=usuario, entregas=entregas, cooperados=cooperados)
    else:
        entregas = Entrega.query.filter_by(cooperado_nome=usuario).all()
        return render_template("painel_coop.html", usuario=usuario, entregas=entregas)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/nova_entrega", methods=["POST"])
def nova_entrega():
    if session.get("tipo") != "adm":
        return redirect("/painel")
    cliente = request.form["cliente"]
    bairro = request.form["bairro"]
    valor = float(request.form["valor"])
    cooperado = request.form["cooperado"]
    entrega = Entrega(cliente=cliente, bairro=bairro, valor=valor, cooperado_nome=cooperado)
    db.session.add(entrega)
    db.session.commit()
    return redirect("/painel")

@app.route("/mudar_status/<int:id>", methods=["POST"])
def mudar_status(id):
    nova = request.form["status"]
    entrega = Entrega.query.get(id)
    if entrega and (session["tipo"] == "adm" or entrega.cooperado_nome == session["usuario"]):
        entrega.status = nova
        db.session.commit()
    return redirect("/painel")

@app.route("/exportar")
def exportar():
    entregas = Entrega.query.all()
    data = [{
        "ID": e.id,
        "Cliente": e.cliente,
        "Bairro": e.bairro,
        "Valor": e.valor,
        "Cooperado": e.cooperado_nome,
        "Status": e.status
    } for e in entregas]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Entregas")
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="entregas.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)