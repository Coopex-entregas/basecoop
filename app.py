from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Troque para algo seguro
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo Usuário
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

# Rota Home
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Rota Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form.get('nome')
        senha = request.form.get('senha')
        if not nome or not senha:
            flash('Preencha nome e senha.')
            return redirect(url_for('login'))

        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and usuario.check_senha(senha):
            session['user_id'] = usuario.id
            session['user_nome'] = usuario.nome
            return redirect(url_for('dashboard'))
        else:
            flash('Nome ou senha incorretos.')
            return redirect(url_for('login'))

    return render_template('login.html')

# Rota Dashboard (área protegida)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Faça login antes.')
        return redirect(url_for('login'))
    return f"Olá, {session['user_nome']}! Bem-vindo ao painel."

# Rota Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.')
    return redirect(url_for('login'))

# Criar banco e usuário admin de teste
@app.before_first_request
def criar_banco():
    db.create_all()
    admin = Usuario.query.filter_by(nome='admin').first()
    if not admin:
        admin = Usuario(nome='admin')
        admin.set_senha('123456')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
