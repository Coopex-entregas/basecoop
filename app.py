from flask import Flask
from config import Config
from models import db
from routes import main

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Blueprint
    app.register_blueprint(main)

    return app

# Executar diretamente
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
