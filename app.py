from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, time, timezone
from models import db, Usuario, Entrega
import pytz

# ... seu código anterior permanece ...

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
        fila_espera = Usuario.query.filter_by(tipo="cooperado", em_fila_espera=True).all()
        entregas = Entrega.query.filter(
            Entrega.hora_pedido >= inicio_dia,
            Entrega.hora_pedido <= fim_dia
        ).order_by(Entrega.hora_pedido.desc()).all()
        return render_template("dashboard_admin.html",
                               cooperados=cooperados,
                               fila_espera=fila_espera,
                               entregas=entregas,
                               data_filtro=data_filtro_str)

    entregas = Entrega.query.filter(
        Entrega.cooperado_id == session["usuario_id"],
        Entrega.hora_pedido >= inicio_dia,
        Entrega.hora_pedido <= fim_dia
    ).order_by(Entrega.hora_pedido.desc()).all()
    return render_template("dashboard_cooperado.html", entregas=entregas)

@app.route("/alterar_fila_espera/<int:cooperado_id>", methods=["POST"])
def alterar_fila_espera(cooperado_id):
    if session.get("usuario_tipo") != "adm":
        flash("Acesso restrito.", "error")
        return redirect(url_for("dashboard"))

    cooperado = Usuario.query.filter_by(id=cooperado_id, tipo="cooperado").first()
    if not cooperado:
        flash("Cooperado não encontrado.", "error")
        return redirect(url_for("dashboard"))

    # Alterna o estado do campo em_fila_espera
    cooperado.em_fila_espera = not cooperado.em_fila_espera
    db.session.commit()
    status = "adicionado" if cooperado.em_fila_espera else "removido"
    flash(f"Cooperado '{cooperado.nome}' {status} da fila de espera.", "success")
    return redirect(url_for("dashboard"))

# ... restante do seu código ...
