from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ===============================
# PRODUCTOS
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
# USUARIOS
# ===============================
class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), default="usuario")
    cedula = db.Column(db.String(10), unique=True, nullable=False)

    solicitudes = db.relationship("Solicitud", backref="usuario", lazy=True)

    def get_id(self):
        return str(self.id_usuario)


# ===============================
# PRODUCTORES
# ===============================
class Productor(db.Model):
    __tablename__ = "productores"

    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100))
    apellidos = db.Column(db.String(100))
    correo = db.Column(db.String(100))
    cedula = db.Column(db.String(10), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    sexo = db.Column(db.String(20))
    provincia = db.Column(db.String(100))
    canton = db.Column(db.String(100))
    parroquia = db.Column(db.String(100))
    autoidentificacion = db.Column(db.String(100))
    indigena_cual = db.Column(db.String(100))
    asociacion = db.Column(db.String(200))

    # Relación con solicitudes (opcional)
    solicitudes = db.relationship("Solicitud", backref="productor", lazy=True, foreign_keys="Solicitud.cedula")


# ===============================
# SOLICITUDES
# ===============================
class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(10), db.ForeignKey("productores.cedula"), nullable=False)

    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)

    estado = db.Column(db.String(50), default="En revisión")

    # 🔥 FECHA AUTOMÁTICA
    fecha = db.Column(db.DateTime, default=datetime.utcnow)