from app import app, db, criar_admin

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        criar_admin()
        print("Banco de dados criado e admin criado.")
