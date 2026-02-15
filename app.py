import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ---------------- CONFIGURACIÓN BD ----------------
database_url = os.getenv("DATABASE_URL")

if database_url:
    # 🔥 Para Render (PostgreSQL)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # 💻 Para tu PC (SQLite)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subvenciones.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# 🔥 Crear tablas automáticamente cuando arranca la app
@app.before_first_request
def crear_tablas():
    db.create_all()


# ---------------- MODELO ----------------
class Solicitud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(10), nullable=False)
    subvencion = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), default="En revisión")


# ---------------- RUTA PRINCIPAL ----------------
@app.route("/")
def index():
    sistema = "Sistema de Subvenciones"
    descripcion = "Registro y consulta de subvenciones agrícolas en Ecuador"

    subvenciones = [
        {"nombre": "Bono Agrícola", "tipo": "bono"},
        {"nombre": "Crédito Productivo", "tipo": "credito"},
    ]

    estadisticas = {
        "solicitantes_registrados": Solicitud.query.count(),
    }

    return render_template(
        "index.html",
        sistema=sistema,
        descripcion=descripcion,
        subvenciones=subvenciones,
        estadisticas=estadisticas,
    )


# ---------------- FORMULARIO ----------------
@app.route("/solicitar", methods=["GET", "POST"])
def solicitar():
    if request.method == "POST":
        cedula = request.form["cedula"]
        tipo = request.form["subvencion"]

        nueva = Solicitud(cedula=cedula, subvencion=tipo)
        db.session.add(nueva)
        db.session.commit()

        return redirect(url_for("exito"))

    return render_template("solicitar.html")


# ---------------- PÁGINA DE ÉXITO ----------------
@app.route("/exito")
def exito():
    return "<h2>✅ Solicitud guardada correctamente</h2><a href='/'>Volver al inicio</a>"


# ---------------- LISTA DE SOLICITUDES ----------------
@app.route("/solicitudes")
def listar_solicitudes():
    lista = Solicitud.query.all()
    return render_template("solicitudes.html", solicitudes=lista)


# ---------------- BUSCAR POR CÉDULA ----------------
@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    resultados = []

    if request.method == "POST":
        cedula = request.form["cedula"]
        resultados = Solicitud.query.filter_by(cedula=cedula).all()

    return render_template("buscar.html", resultados=resultados)


# ---------------- CAMBIAR ESTADO ----------------
@app.route("/estado/<int:id>/<nuevo_estado>")
def cambiar_estado(id, nuevo_estado):
    solicitud = Solicitud.query.get_or_404(id)

    if nuevo_estado in ["Aprobado", "Rechazado"]:
        solicitud.estado = nuevo_estado
        db.session.commit()

    return redirect(url_for("listar_solicitudes"))


# ---------------- EJECUCIÓN LOCAL ----------------
if __name__ == "__main__":
    app.run(debug=True)