from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'chave_super_secreta'

# Usuários fixos para exemplo (username: senha, tipo)
users = {
    'coopex': {'password': '05062721', 'role': 'admin'},
    'coop1': {'password': 'senha1', 'role': 'cooperado'},
    'coop2': {'password': 'senha2', 'role': 'cooperado'}
}

# Dados de entregas de exemplo
entregas = [
    {'id': 1, 'cooperado': 'coop1', 'cliente': 'Cliente A', 'valor': 50, 'status': 'Pendente'},
    {'id': 2, 'cooperado': 'coop2', 'cliente': 'Cliente B', 'valor': 70, 'status': 'Pago'},
    {'id': 3, 'cooperado': 'coop1', 'cliente': 'Cliente C', 'valor': 40, 'status': 'Pago'},
]

@app.route('/')
def home():
    if 'user' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('dashboard_admin'))
        else:
            return redirect(url_for('dashboard_cooperado'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)
        if user and user['password'] == password:
            session['user'] = username
            session['role'] = user['role']
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/dashboard/admin')
def dashboard_admin():
    if session.get('role') != 'admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    return render_template('dashboard_admin.html', entregas=entregas)

@app.route('/dashboard/cooperado')
def dashboard_cooperado():
    if session.get('role') != 'cooperado':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))
    user = session.get('user')
    entregas_user = [e for e in entregas if e['cooperado'] == user]
    return render_template('dashboard_cooperado.html', entregas=entregas_user, cooperado=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
