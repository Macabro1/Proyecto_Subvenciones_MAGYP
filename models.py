from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ===============================
# TABLA PRODUCTOS
# ===============================
class ProductoDB(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    subsidio = db.Column(db.Integer, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)

    solicitudes = db.relationship("Solicitud", backref="producto", lazy=True)


# ===============================
# TABLA SOLICITUDES
# ===============================
class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(50), default="En revisión")

    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"))


# ===============================
# TABLA USUARIOS (REQUERIDA)
# ===============================
class Usuario(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    mail = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)