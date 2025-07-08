from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Simulação de dados em memória
entregas = []
cooperados = {
    'cooperado1': '123',
    'cooperado2': '456',
}
# Login fixo do admin
ADMIN_USER = 'admin'
ADMIN_PASS = '05062721'

@app.route('/')
def home():
    if 'user' in session:
        if session['user'] == ADMIN_USER:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('cooperado_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['user'].strip().lower()
        password = request.form['password']

        if user == ADMIN_USER and password == ADMIN_PASS:
            session['user'] = ADMIN_USER
            return redirect(url_for('admin_dashboard'))

        if user in cooperados and cooperados[user] == password:
            session['user'] = user
            return redirect(url_for('cooperado_dashboard'))

        return "Usuário ou senha inválidos", 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ADMIN DASHBOARD
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user' not in session or session['user'] != ADMIN_USER:
        return redirect(url_for('login'))

    global entregas, cooperados

    if request.method == 'POST':
        # Pode cadastrar entrega ou cooperado dependendo do form enviado
        if 'nova_entrega' in request.form:
            cliente = request.form.get('cliente', '').strip()
            bairro = request.form.get('bairro', '').strip()
            valor = float(request.form.get('valor', 0) or 0)
            status = request.form.get('status', 'Pendente')
            cooperado = request.form.get('cooperado', '').strip().lower() or None

            nova_id = max([e['id'] for e in entregas], default=0) + 1
            entregas.append({
                'id': nova_id,
                'cliente': cliente,
                'bairro': bairro,
                'valor': valor,
                'status': status,
                'cooperado': cooperado
            })
        elif 'novo_cooperado' in request.form:
            coop_name = request.form.get('coop_name', '').strip().lower()
            coop_pass = request.form.get('coop_pass', '').strip()
            if coop_name and coop_pass:
                cooperados[coop_name] = coop_pass

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_dashboard.html', entregas=entregas, cooperados=cooperados)

# COOPERADO DASHBOARD
@app.route('/cooperado', methods=['GET', 'POST'])
def cooperado_dashboard():
    if 'user' not in session or session['user'] == ADMIN_USER:
        return redirect(url_for('login'))

    user = session['user']
    global entregas

    if request.method == 'POST':
        # Cooperado pode atualizar status de suas entregas
        entrega_id = int(request.form.get('entrega_id'))
        novo_status = request.form.get('status', 'Pendente')
        for e in entregas:
            if e['id'] == entrega_id and e.get('cooperado') == user:
                e['status'] = novo_status
                break
        return redirect(url_for('cooperado_dashboard'))

    entregas_user = [e for e in entregas if e.get('cooperado') == user]
    return render_template('cooperado_dashboard.html', entregas=entregas_user, usuario=user)

# Exportar Excel (só admin)
@app.route('/exportar_excel')
def exportar_excel():
    if 'user' not in session or session['user'] != ADMIN_USER:
        return redirect(url_for('login'))

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
