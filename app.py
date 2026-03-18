import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from models import db, ProductoDB, Solicitud, Usuario
from inventario_poo import Inventario

from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# ===============================
# IMPORT PERSISTENCIA
# ===============================

from inventario.persistencia import (
    guardar_txt, guardar_json, guardar_csv,
    leer_txt, leer_json, leer_csv,
    limpiar_archivos
)

# ===============================
# CONFIGURACIÓN APP
# ===============================

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
inventario = Inventario()

# ===============================
# FLASK LOGIN
# ===============================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Permite usar current_user en HTML
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ===============================
# VALIDACIÓN CÉDULA
# ===============================

def validar_cedula_ecuatoriana(cedula):

    if len(cedula) != 10 or not cedula.isdigit():
        return False

    provincia = int(cedula[:2])
    if provincia < 1 or provincia > 24:
        return False

    tercer_digito = int(cedula[2])
    if tercer_digito >= 6:
        return False

    coeficientes = [2,1,2,1,2,1,2,1,2]
    suma = 0

    for i in range(9):
        valor = int(cedula[i]) * coeficientes[i]
        if valor >= 10:
            valor -= 9
        suma += valor

    digito_verificador = (10 - (suma % 10)) % 10

    return digito_verificador == int(cedula[9])

# ===============================
# CARGAR PRODUCTOS INICIALES
# ===============================

def cargar_productos_iniciales():

    if ProductoDB.query.count() == 0:

        productos_iniciales = [
            ("Arroz",180,70,20),
            ("Papa",200,75,15),
            ("Cacao",250,80,10),
            ("Maíz duro",150,70,25),
            ("Maíz suave",160,70,25),
            ("Aguacate",300,60,12),
            ("Banano",220,65,18),
            ("Tomate",140,70,30),
            ("Café",280,75,14),
            ("Pitahaya",320,60,8),
            ("Maracuyá",210,65,20),
            ("Palma aceitera",350,70,10),
            ("Caña de azúcar",190,70,22),
            ("Cebolla colorada",130,75,28),
            ("Chocho",170,70,16),
            ("Mora",240,65,14),
            ("Guanábana",260,60,9)
        ]

        for nombre, precio, subsidio, cantidad in productos_iniciales:
            nuevo = ProductoDB(
                nombre=nombre,
                precio=precio,
                subsidio=subsidio,
                cantidad=cantidad
            )
            db.session.add(nuevo)

        db.session.commit()

# Crear tablas
with app.app_context():
    db.create_all()
    cargar_productos_iniciales()

# ===============================
# REGISTRO
# ===============================

@app.route("/registro", methods=["GET","POST"])
def registro():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":

        nombre = request.form["nombre"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        existe = Usuario.query.filter_by(email=email).first()

        if existe:
            flash("El correo ya está registrado", "danger")
            return redirect(url_for("registro"))

        nuevo_usuario = Usuario(
            nombre=nombre,
            email=email,
            password=password
        )

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Registro exitoso. Ahora puedes iniciar sesión", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")

# ===============================
# LOGIN
# ===============================

@app.route("/login", methods=["GET","POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):
            login_user(usuario)
            flash("Bienvenido al sistema", "success")
            return redirect(url_for("index"))

        flash("Credenciales incorrectas", "danger")

    return render_template("login.html")

# ===============================
# LOGOUT
# ===============================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for("login"))

# ===============================
# CARGAR INVENTARIO
# ===============================

@app.before_request
def cargar_inventario():
    productos = ProductoDB.query.all()
    inventario.cargar_desde_db(productos)

# ===============================
# HOME
# ===============================

@app.route("/")
@login_required
def index():

    total_solicitudes = Solicitud.query.count()
    aprobadas = Solicitud.query.filter_by(estado="Aprobado").count()
    rechazadas = Solicitud.query.filter_by(estado="Rechazado").count()

    productos = ProductoDB.query.all()

    return render_template(
        "index.html",
        productos=productos,
        total_solicitudes=total_solicitudes,
        aprobadas=aprobadas,
        rechazadas=rechazadas
    )

# ===============================
# SOLICITUDES
# ===============================

@app.route("/solicitar", methods=["POST"])
@login_required
def solicitar():

    cedula = request.form["cedula"]
    producto_id = request.form["producto_id"]

    if not validar_cedula_ecuatoriana(cedula):
        flash("Cédula ecuatoriana inválida", "danger")
        return redirect(url_for("index"))

    nueva = Solicitud(
        cedula=cedula,
        producto_id=producto_id,
        estado="En revisión"
    )

    db.session.add(nueva)
    db.session.commit()

    flash("Solicitud enviada correctamente", "success")
    return redirect(url_for("index"))

@app.route("/solicitudes")
@login_required
def listar_solicitudes():
    solicitudes = Solicitud.query.all()
    return render_template("solicitudes.html", solicitudes=solicitudes)

# ===============================
# APROBAR / RECHAZAR
# ===============================

@app.route("/estado/<int:id>/<nuevo_estado>")
@login_required
def cambiar_estado(id, nuevo_estado):

    solicitud = Solicitud.query.get_or_404(id)

    if solicitud.estado == "Aprobado":
        return redirect(url_for("listar_solicitudes"))

    if nuevo_estado == "Aprobado":

        producto = solicitud.producto

        if producto.cantidad <= 0:
            flash("No hay stock disponible", "danger")
            return redirect(url_for("listar_solicitudes"))

        producto.cantidad -= 1
        solicitud.estado = "Aprobado"
        flash("Solicitud aprobada", "success")

    elif nuevo_estado == "Rechazado":
        solicitud.estado = "Rechazado"
        flash("Solicitud rechazada", "warning")

    db.session.commit()
    return redirect(url_for("listar_solicitudes"))

# ===============================
# INVENTARIO
# ===============================

@app.route("/inventario")
@login_required
def ver_inventario():
    productos = ProductoDB.query.all()
    return render_template("inventario.html", productos=productos)

@app.route("/agregar_producto", methods=["POST"])
@login_required
def agregar_producto():

    nuevo = ProductoDB(
        nombre=request.form["nombre"],
        precio=float(request.form["precio"]),
        subsidio=float(request.form["subsidio"]),
        cantidad=int(request.form["cantidad"])
    )

    db.session.add(nuevo)
    db.session.commit()

    flash("Producto agregado correctamente", "success")
    return redirect(url_for("ver_inventario"))

@app.route("/eliminar_producto/<int:id>")
@login_required
def eliminar_producto(id):

    producto = ProductoDB.query.get_or_404(id)

    db.session.delete(producto)
    db.session.commit()

    flash("Producto eliminado", "warning")
    return redirect(url_for("ver_inventario"))

# ===============================
# PERSISTENCIA
# ===============================

@app.route("/guardar_archivos", methods=["POST"])
@login_required
def guardar_archivos():

    nombre = request.form["nombre"]
    cedula = request.form["cedula"]

    if not validar_cedula_ecuatoriana(cedula):
        flash("Cédula inválida", "danger")
        return redirect(url_for("ver_datos"))

    guardar_txt(nombre, cedula)
    guardar_json(nombre, cedula)
    guardar_csv(nombre, cedula)

    flash("Datos guardados en archivos", "success")
    return redirect(url_for("ver_datos"))

@app.route("/datos")
@login_required
def ver_datos():

    datos_txt = leer_txt()
    datos_json = leer_json()
    datos_csv = leer_csv()

    return render_template(
        "datos.html",
        datos_txt=datos_txt,
        datos_json=datos_json,
        datos_csv=datos_csv
    )

@app.route("/limpiar_datos")
@login_required
def limpiar_datos():
    limpiar_archivos()
    flash("Datos eliminados", "info")
    return redirect(url_for("ver_datos"))

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    app.run(debug=True)