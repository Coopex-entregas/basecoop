import os

class Config:
    # Se quiser usar variável de ambiente, por exemplo:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua-chave-secreta-aqui'

    # URL de conexão com o banco PostgreSQL no Render (exemplo)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://usuario:senha@host:porta/nome_do_banco'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Outras configs que quiser adicionar
    DEBUG = False
