from app import app, db, inicializar_datos_ecuador

with app.app_context():
    db.create_all()
    inicializar_datos_ecuador()
    print("Base de datos inicializada correctamente")