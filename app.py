from flask import Flask, render_template, request, redirect, url_for, send_file
import io
import pandas as pd

app = Flask(__name__)

# Dados simulados
entregas = [
    {'id': 1, 'cliente': 'Cliente A', 'bairro': 'Centro', 'valor': 50.0, 'status': 'Pendente', 'cooperado': 'Cooperado 2'},
    {'id': 2, 'cliente': 'Cliente B', 'bairro': 'Bairro X', 'valor': 70.0, 'status': 'Pago', 'cooperado': 'Cooperado 1'},
    {'id': 3, 'cliente': 'Cliente C', 'bairro': 'Lagoa Nova', 'valor': 40.0, 'status': 'Pendente', 'cooperado': None},
]

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    global entregas

    if request.method == 'POST':
        # Alterar status e cooperado de uma entrega existente
        if 'alterar_status_id' in request.form:
            eid = int(request.form['alterar_status_id'])
            novo_status = request.form.get('novo_status', 'Pendente')
            novo_cooperado = request.form.get('novo_cooperado', '').strip() or None

            for e in entregas:
                if e['id'] == eid:
                    e['status'] = novo_status
                    e['cooperado'] = novo_cooperado
                    break
            return redirect(url_for('admin_dashboard'))

        # Cadastrar nova entrega
        cliente = request.form.get('cliente', '').strip()
        if cliente:
            bairro = request.form.get('bairro', '').strip()
            valor = float(request.form.get('valor', 0) or 0)
            status = request.form.get('status', 'Pendente')
            cooperado = request.form.get('cooperado', '').strip() or None

            nova_id = max([e['id'] for e in entregas]) + 1 if entregas else 1
            entregas.append({
                'id': nova_id,
                'cliente': cliente,
                'bairro': bairro,
                'valor': valor,
                'status': status,
                'cooperado': cooperado
            })
            return redirect(url_for('admin_dashboard'))

    entregas_com_cooperado = [e for e in entregas if e['cooperado']]
    entregas_sem_cooperado = [e for e in entregas if not e['cooperado']]

    return render_template('admin_dashboard.html',
                           entregas_com_cooperado=entregas_com_cooperado,
                           entregas_sem_cooperado=entregas_sem_cooperado)

@app.route('/cooperado/<nome>', methods=['GET', 'POST'])
def cooperado_dashboard(nome):
    global entregas
    entregas_do_cooperado = [e for e in entregas if e['cooperado'] == nome]

    if request.method == 'POST':
        entrega_id = int(request.form['entrega_id'])
        novo_status = request.form.get('novo_status', 'Pendente')
        for e in entregas:
            if e['id'] == entrega_id and e['cooperado'] == nome:
                e['status'] = novo_status
                break
        return redirect(url_for('cooperado_dashboard', nome=nome))

    return render_template('cooperado_dashboard.html', cooperado=nome, entregas=entregas_do_cooperado)

@app.route('/exportar_excel')
def exportar_excel():
    df = pd.DataFrame(entregas)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Entregas')
    output.seek(0)
    return send_file(
        output,
        download_name="relatorio_entregas.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    app.run(debug=True)
