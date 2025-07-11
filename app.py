# app.py
import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timezone
from models import db, Usuario, Entrega
from sqlalchemy import func
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
        "cadastrar_entrega", "editar_entrega", "excluir_entrega", "exportar_entrega
