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

    codigo_subsidio = db.Column(
        db.String(10),
        db.ForeignKey("subsidio.codigo_subsidio"),
        nullable=True
    )

    cantidad = db.Column(db.Integer, nullable=False)

    solicitudes = db.relationship(
        "Solicitud",
        backref="producto",
        lazy=True,
        cascade="all, delete"
    )


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

    solicitudes = db.relationship(
        "Solicitud",
        backref="usuario",
        lazy=True
    )

    evaluaciones = db.relationship(
        "Evaluacion",
        backref="evaluador",
        lazy=True
    )

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

    solicitudes = db.relationship(
        "Solicitud",
        backref="productor",
        lazy=True,
        primaryjoin="Productor.cedula==Solicitud.cedula"
    )


# ===============================
# SOLICITUDES (🔥 CORREGIDO)
# ===============================
class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    # 🔥 MAPEO REAL A TU BD
    id = db.Column("id_solicitud", db.Integer, primary_key=True)

    cedula = db.Column(
        db.String(10),
        db.ForeignKey("productores.cedula"),
        nullable=False
    )

    producto_id = db.Column(
        db.Integer,
        db.ForeignKey("productos.id"),
        nullable=False
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario"),
        nullable=False
    )

    estado = db.Column(db.String(50), default="En revisión")
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    evaluacion = db.relationship(
        "Evaluacion",
        backref="solicitud",
        uselist=False,
        cascade="all, delete-orphan"
    )


# ===============================
# EVALUACIÓN
# ===============================
class Evaluacion(db.Model):
    __tablename__ = "evaluacion"

    id_evaluacion = db.Column(db.Integer, primary_key=True)

    observaciones = db.Column(db.Text)
    puntaje_total = db.Column(db.Float, default=0)
    resultado = db.Column(db.String(50))

    id_solicitud = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes.id_solicitud"),
        nullable=False,
        unique=True
    )

    evaluado_por = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id_usuario")
    )

    fecha_evaluacion = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    firma_digital = db.Column(db.String(256))

    criterios = db.relationship(
        "CriterioEvaluacion",
        backref="evaluacion",
        lazy="joined",
        cascade="all, delete-orphan"
    )


# ===============================
# CRITERIOS DE EVALUACIÓN
# ===============================
class CriterioEvaluacion(db.Model):
    __tablename__ = "criterio_evaluacion"

    id_criterio = db.Column(db.Integer, primary_key=True)

    id_evaluacion = db.Column(
        db.Integer,
        db.ForeignKey("evaluacion.id_evaluacion"),
        nullable=False
    )

    criterio = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    puntaje = db.Column(db.Float)


# ===============================
# SUBSIDIO
# ===============================
class Subsidio(db.Model):
    __tablename__ = "subsidio"

    codigo_subsidio = db.Column(db.String(10), primary_key=True)
    nombre_programa = db.Column(db.String(150))
    descripcion = db.Column(db.Text)

    productos = db.relationship(
        "ProductoDB",
        backref="subsidio_rel",
        lazy=True
    )