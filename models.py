from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # "adm" ou "cooperado"

    entregas = db.relationship("Entrega", backref="cooperado", lazy=True)

    def __repr__(self):
        return f"<Usuario {self.nome} ({self.tipo})>"

class Entrega(db.Model):
    __tablename__ = "entrega"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=True)
    hora_pedido = db.Column(db.DateTime, nullable=False)
    hora_atribuida = db.Column(db.DateTime, nullable=True)
    cooperado_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    status_pagamento = db.Column(db.String(20), nullable=False, default="pendente")
    status_entrega = db.Column(db.String(20), nullable=False, default="pendente")

    def __repr__(self):
        return f"<Entrega #{self.id} - {self.descricao}>"
