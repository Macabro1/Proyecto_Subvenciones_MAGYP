from flask import Flask, render_template, request, redirect, url_for
from config import Config
from models import db, ProductoDB, Solicitud
from inventario_poo import Inventario

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# ===============================
# INICIALIZAR INVENTARIO POO
# ===============================
inventario = Inventario()

# ===============================
# CREAR TABLAS Y CARGAR PRODUCTOS INICIALES
# ===============================
def cargar_productos_iniciales():
    if ProductoDB.query.count() == 0:
        productos_iniciales = [
            ("Arroz", 180, 70, 20),
            ("Papa", 200, 75, 15),
            ("Cacao", 250, 80, 10),
            ("Maíz duro", 150, 70, 25),
            ("Maíz suave", 160, 70, 25),
            ("Aguacate", 300, 60, 12),
            ("Banano", 220, 65, 18),
            ("Tomate", 140, 70, 30),
            ("Café", 280, 75, 14),
            ("Pitahaya", 320, 60, 8),
            ("Maracuyá", 210, 65, 20),
            ("Palma aceitera", 350, 70, 10),
            ("Caña de azúcar", 190, 70, 22),
            ("Cebolla colorada", 130, 75, 28),
            ("Chocho", 170, 70, 16),
            ("Mora", 240, 65, 14),
            ("Guanábana", 260, 60, 9),
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
        print("✔ Inventario inicial cargado correctamente")


with app.app_context():
    db.create_all()
    cargar_productos_iniciales()

# ===============================
# CARGAR INVENTARIO POO ANTES DE CADA REQUEST
# ===============================
@app.before_request
def cargar_inventario():
    productos = ProductoDB.query.all()
    inventario.cargar_desde_db(productos)

# ===============================
# HOME
# ===============================
@app.route("/")
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
# CREAR SOLICITUD
# ===============================
@app.route("/solicitar", methods=["POST"])
def solicitar():

    cedula = request.form["cedula"]
    producto_id = request.form["producto_id"]

    nueva = Solicitud(
        cedula=cedula,
        producto_id=producto_id,
        estado="En revisión"
    )

    db.session.add(nueva)
    db.session.commit()

    return redirect(url_for("index"))

# ===============================
# LISTAR SOLICITUDES
# ===============================
@app.route("/solicitudes")
def listar_solicitudes():

    solicitudes = Solicitud.query.all()
    return render_template("solicitudes.html", solicitudes=solicitudes)

# ===============================
# APROBAR / RECHAZAR
# ===============================
@app.route("/estado/<int:id>/<nuevo_estado>")
def cambiar_estado(id, nuevo_estado):

    solicitud = Solicitud.query.get_or_404(id)

    # Si ya fue aprobada no volver a descontar
    if solicitud.estado == "Aprobado":
        return redirect(url_for("listar_solicitudes"))

    if nuevo_estado == "Aprobado":

        producto = solicitud.producto

        if producto.cantidad <= 0:
            return "No hay stock disponible"

        producto.cantidad -= 1
        solicitud.estado = "Aprobado"

        db.session.commit()

    elif nuevo_estado == "Rechazado":
        solicitud.estado = "Rechazado"
        db.session.commit()

    return redirect(url_for("listar_solicitudes"))

# ===============================
# INVENTARIO CRUD
# ===============================
@app.route("/inventario")
def ver_inventario():

    productos = ProductoDB.query.all()
    return render_template("inventario.html", productos=productos)

@app.route("/agregar_producto", methods=["POST"])
def agregar_producto():

    nuevo = ProductoDB(
        nombre=request.form["nombre"],
        precio=float(request.form["precio"]),
        subsidio=float(request.form["subsidio"]),
        cantidad=int(request.form["cantidad"])
    )

    db.session.add(nuevo)
    db.session.commit()

    return redirect(url_for("ver_inventario"))

@app.route("/eliminar_producto/<int:id>")
def eliminar_producto(id):

    producto = ProductoDB.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()

    return redirect(url_for("ver_inventario"))

# ===============================
# EJECUTAR APP
# ===============================
if __name__ == "__main__":
    app.run(debug=True)