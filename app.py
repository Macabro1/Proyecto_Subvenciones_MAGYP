import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, jsonify
from config import Config
from models import db, ProductoDB, Solicitud, Usuario
from services.producto_service import obtener_productos
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from reportlab.platypus import SimpleDocTemplate, Table
from datetime import datetime
from io import BytesIO

# 🔥 PERSISTENCIA
from inventario.persistencia import (
    guardar_txt, guardar_json, guardar_csv,
    leer_txt, leer_json, leer_csv,
    limpiar_archivos
)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "clave_secreta"

db.init_app(app)

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ================= ADMIN =================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ================= INIT =================
def cargar_productos():
    if ProductoDB.query.count() == 0:
        productos = [
            ("Arroz",180,70,20),
            ("Papa",200,75,15),
            ("Cacao",250,80,10),
            ("Maíz duro",150,70,25),
            ("Maíz suave",160,70,25),
            ("Aguacate",300,60,12),
            ("Banano",220,65,18),
            ("Tomate",140,70,30),
            ("Café",280,75,14)
        ]
        for n, p, s, c in productos:
            db.session.add(ProductoDB(nombre=n, precio=p, subsidio=s, cantidad=c))
        db.session.commit()

def crear_admin():
    if not Usuario.query.filter_by(email="admin@admin.com").first():
        admin = Usuario(
            nombre="Admin",
            email="admin@admin.com",
            password=generate_password_hash("admin123"),
            rol="admin"
        )
        db.session.add(admin)
        db.session.commit()

with app.app_context():
    db.create_all()
    cargar_productos()
    crear_admin()

# ================= AUTH =================
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        if Usuario.query.filter_by(email=request.form["email"]).first():
            flash("Correo ya existe", "danger")
            return redirect(url_for("registro"))

        nuevo = Usuario(
            nombre=request.form["nombre"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"]),
            rol="usuario"
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Usuario registrado", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Usuario.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            if user.rol == "admin":
                return redirect(url_for("listar_solicitudes"))
            return redirect(url_for("index"))

        flash("Credenciales incorrectas", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ================= HOME =================
@app.route("/")
@login_required
def index():
    solicitud_activa = Solicitud.query.filter_by(
        usuario_id=current_user.id_usuario,
        estado="En revisión"
    ).first()

    return render_template(
        "index.html",
        productos=obtener_productos(),
        solicitud_activa=solicitud_activa
    )

# ================= SOLICITAR =================
@app.route("/solicitar", methods=["POST"])
@login_required
def solicitar():
    existente = Solicitud.query.filter_by(
        usuario_id=current_user.id_usuario,
        estado="En revisión"
    ).first()

    if existente:
        flash("Ya tienes una solicitud activa", "warning")
        return redirect(url_for("index"))

    producto_id = request.form.get("producto_id")
    cedula_productor = request.form.get("cedula")

    if not cedula_productor:
        flash("Debes seleccionar un productor", "danger")
        return redirect(url_for("index"))

    if not producto_id:
        flash("Debes seleccionar un producto", "danger")
        return redirect(url_for("index"))

    nueva_solicitud = Solicitud(
        usuario_id=current_user.id_usuario,
        cedula=cedula_productor,
        producto_id=int(producto_id),
        fecha=datetime.now(),
        estado="En revisión"
    )

    db.session.add(nueva_solicitud)
    db.session.commit()

    flash("Solicitud enviada correctamente", "success")
    return redirect(url_for("index"))

# ================= LISTAR SOLICITUDES =================
@app.route("/solicitudes")
@login_required
@admin_required
def listar_solicitudes():
    solicitudes = Solicitud.query.all()
    return render_template("solicitudes.html", solicitudes=solicitudes)

# ================= MIS SOLICITUDES =================
@app.route("/mis_solicitudes")
@login_required
def mis_solicitudes():
    solicitudes = Solicitud.query.filter_by(usuario_id=current_user.id_usuario).all()
    return render_template("mis_solicitudes.html", solicitudes=solicitudes)

# ================= CANCELAR =================
@app.route("/cancelar_solicitud/<int:id>")
@login_required
def cancelar_solicitud(id):
    solicitud = db.session.get(Solicitud, id)

    if not solicitud:
        flash("Solicitud no encontrada", "danger")
        return redirect(url_for("mis_solicitudes"))

    if solicitud.usuario_id != current_user.id_usuario:
        flash("No tienes permiso", "danger")
        return redirect(url_for("mis_solicitudes"))

    db.session.delete(solicitud)
    db.session.commit()
    flash("Solicitud cancelada", "success")
    return redirect(url_for("mis_solicitudes"))

# ================= CAMBIAR ESTADO =================
@app.route("/cambiar_estado/<int:id>/<nuevo_estado>")
@login_required
@admin_required
def cambiar_estado(id, nuevo_estado):
    solicitud = db.session.get(Solicitud, id)

    if solicitud:
        solicitud.estado = nuevo_estado
        db.session.commit()
        flash(f"Estado cambiado a {nuevo_estado}", "success")
    else:
        flash("Solicitud no encontrada", "danger")

    return redirect(url_for("listar_solicitudes"))

# ================= AUTOCOMPLETE =================
@app.route("/buscar_productor")
@login_required
def buscar_productor():
    cedula = request.args.get("cedula", "").strip().replace(" ", "")

    if not cedula:
        return jsonify({})

    productor = db.session.execute(
        db.text("""
            SELECT nombres, apellidos, correo, telefono, provincia, canton, parroquia, sexo
            FROM productores
            WHERE REPLACE(cedula, ' ', '') = :cedula
        """),
        {"cedula": cedula}
    ).fetchone()

    if not productor:
        return jsonify({})

    return jsonify({
        "nombres": productor[0],
        "apellidos": productor[1],
        "correo": productor[2],
        "telefono": productor[3],
        "provincia": productor[4],
        "canton": productor[5],
        "parroquia": productor[6],
        "sexo": productor[7]
    })

# ================= INVENTARIO =================
@app.route("/inventario")
@login_required
def mostrar_inventario():
    return render_template("inventario.html", productos=obtener_productos())

@app.route("/agregar_producto", methods=["POST"])
@login_required
@admin_required
def agregar_producto():
    nombre = request.form.get("nombre")
    precio = request.form.get("precio", type=float)
    subsidio = request.form.get("subsidio", type=int)
    cantidad = request.form.get("cantidad", type=int)

    if nombre and precio is not None:
        producto = ProductoDB(nombre=nombre, precio=precio, subsidio=subsidio, cantidad=cantidad)
        db.session.add(producto)
        db.session.commit()
        flash("Producto agregado correctamente", "success")
    else:
        flash("Datos incompletos", "danger")

    return redirect(url_for("mostrar_inventario"))

@app.route("/eliminar_producto/<int:id>")
@login_required
@admin_required
def eliminar_producto_route(id):
    producto = db.session.get(ProductoDB, id)

    if producto:
        db.session.delete(producto)
        db.session.commit()
        flash("Producto eliminado correctamente", "success")
    else:
        flash("Producto no encontrado", "danger")

    return redirect(url_for("mostrar_inventario"))

# ================= PDF =================
@app.route("/reporte_pdf")
@login_required
def reporte_pdf():
    productos = obtener_productos()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)

    data = [["Producto", "Precio", "Subsidio", "Cantidad"]]
    for p in productos:
        data.append([p.nombre, p.precio, p.subsidio, p.cantidad])

    doc.build([Table(data)])
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="inventario.pdf", mimetype="application/pdf")

# 🔥 FIX ERROR
@app.route("/reporte_producto_pdf")
@login_required
def reporte_producto_pdf():
    return reporte_pdf()

# ================= REPORTE SEXO =================
@app.route("/reporte_sexo_pdf")
@login_required
def reporte_sexo_pdf():
    solicitudes = Solicitud.query.all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)

    data = [["Producto", "Cédula", "Sexo", "Fecha", "Estado"]]
    for s in solicitudes:
        data.append([
            s.producto.nombre if s.producto else "",
            s.cedula,
            getattr(s, "sexo", ""),
            s.fecha.strftime("%Y-%m-%d"),
            s.estado
        ])

    doc.build([Table(data)])
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="solicitudes_sexo.pdf", mimetype="application/pdf")

# ================= REPORTE PROVINCIA =================
@app.route("/reporte_provincia_pdf")
@login_required
def reporte_provincia_pdf():
    solicitudes = Solicitud.query.all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)

    data = [["Producto", "Cédula", "Provincia", "Fecha", "Estado"]]
    for s in solicitudes:
        data.append([
            s.producto.nombre if s.producto else "",
            s.cedula,
            getattr(s, "provincia", ""),
            s.fecha.strftime("%Y-%m-%d"),
            s.estado
        ])

    doc.build([Table(data)])
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="solicitudes_provincia.pdf", mimetype="application/pdf")

# ================= DATOS =================
@app.route("/datos")
@login_required
def mostrar_datos():
    return render_template(
        "datos.html",
        datos_txt=leer_txt() or [],
        datos_json=leer_json() or [],
        datos_csv=leer_csv() or []
    )

@app.route("/guardar_archivos", methods=["POST"])
@login_required
def guardar_archivos():
    datos = request.form.to_dict()
    cedula = datos.get("cedula")

    if not cedula:
        flash("Debe ingresar la cédula", "danger")
        return redirect(url_for("mostrar_datos"))

    guardar_txt(datos, cedula)
    guardar_json(datos, cedula)
    guardar_csv(datos, cedula)

    flash("Datos guardados", "success")
    return redirect(url_for("mostrar_datos"))

# ================= LIMPIAR =================
@app.route("/limpiar_datos")
@login_required
def limpiar_datos():
    limpiar_archivos()
    flash("Datos eliminados", "success")
    return redirect(url_for("mostrar_datos"))

# ================= BUSCAR  =================
@app.route("/buscar", methods=["GET", "POST"])
@login_required
def buscar():
    resultados = []

    if request.method == "POST":
        cedula = request.form.get("cedula", "").strip()

        if cedula:
            resultados = Solicitud.query.filter(
                Solicitud.cedula.like(f"%{cedula}%")
            ).all()

    return render_template("buscar.html", resultados=resultados)

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
