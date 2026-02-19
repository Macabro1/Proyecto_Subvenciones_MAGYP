import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# ---------------- CREAR APP ----------------
app = Flask(__name__)

# ---------------- CONFIGURACIÓN BD ----------------
database_url = os.getenv("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///subvenciones.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ---------------- INICIALIZAR BD ----------------
db = SQLAlchemy(app)

# ---------------- MODELO ----------------
class Solicitud(db.Model):
    __tablename__ = "solicitud"

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(10), nullable=False)
    subvencion = db.Column(db.String(50), nullable=False)
    tipo_bono = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), default="En revisión")


# ✅ CREAR TABLAS SOLO UNA VEZ AL INICIAR
with app.app_context():
    db.create_all()


# ---------------- RUTA PRINCIPAL ----------------
@app.route("/")
def index():
    sistema = "Sistema de Subvenciones"
    descripcion = "Registro y consulta de subvenciones agrícolas en Ecuador"

    subvenciones = [
        {"nombre": "Bono Agrícola", "tipo": "bono"},
        {"nombre": "Crédito Productivo", "tipo": "credito"},
    ]

    try:
        total = Solicitud.query.count()
    except Exception:
        total = 0

    estadisticas = {
        "solicitantes_registrados": total,
    }

    return render_template(
        "index.html",
        sistema=sistema,
        descripcion=descripcion,
        subvenciones=subvenciones,
        estadisticas=estadisticas,
    )


# ---------------- SOLICITAR ----------------
@app.route("/solicitar", methods=["GET", "POST"])
def solicitar():
    if request.method == "POST":
        try:
            nueva = Solicitud(
                cedula=request.form["cedula"],
                subvencion=request.form["subvencion"],
                tipo_bono=request.form["tipo_bono"],
            )

            db.session.add(nueva)
            db.session.commit()

            return redirect(url_for("exito"))

        except Exception as e:
            db.session.rollback()
            return f"Error al guardar: {e}"

    return render_template("solicitar.html")


# ---------------- ÉXITO ----------------
@app.route("/exito")
def exito():
    return "<h2>✅ Solicitud guardada correctamente</h2><a href='/'>Volver</a>"


# ---------------- LISTAR ----------------
@app.route("/solicitudes")
def listar_solicitudes():
    try:
        lista = Solicitud.query.all()
        return render_template("solicitudes.html", solicitudes=lista)
    except Exception as e:
        return f"Error al consultar: {e}"


# ---------------- BUSCAR ----------------
@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    resultados = []

    if request.method == "POST":
        try:
            cedula = request.form["cedula"]
            resultados = Solicitud.query.filter_by(cedula=cedula).all()
        except Exception as e:
            return f"Error en búsqueda: {e}"

    return render_template("buscar.html", resultados=resultados)


# ---------------- CAMBIAR ESTADO ----------------
@app.route("/estado/<int:id>/<nuevo_estado>")
def cambiar_estado(id, nuevo_estado):
    solicitud = Solicitud.query.get_or_404(id)

    if nuevo_estado in ["Aprobado", "Rechazado"]:
        solicitud.estado = nuevo_estado
        db.session.commit()

    return redirect(url_for("listar_solicitudes"))


# ---------------- ABOUT ----------------
@app.route("/about")
def about():
    return render_template("about.html")


# ---------------- EJECUCIÓN LOCAL ----------------
if __name__ == "__main__":
    app.run(debug=True)