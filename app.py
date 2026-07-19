import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, jsonify
from config import Config
from models import db, ProductoDB, Solicitud, Usuario, Evaluacion, CriterioEvaluacion
from services.producto_service import obtener_productos
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from reportlab.platypus import SimpleDocTemplate, Table
from datetime import datetime
from io import BytesIO
import qrcode
import base64
#  PERSISTENCIA
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
            rol="admin",
            cedula="0000000000"  # 🔥 OBLIGATORIO
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

        cedula = request.form.get("cedula")

        if not cedula:
            flash("La cédula es obligatoria", "danger")
            return redirect(url_for("registro"))

        nuevo = Usuario(
            nombre=request.form["nombre"],
            email=request.form["email"],
            password=generate_password_hash(request.form["password"]),
            rol="usuario",
            cedula=cedula  # 🔥 AQUÍ ESTÁ LA CLAVE
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

# ================= NUEVA PAGINA INICIO =================
@app.route("/")
def inicio():
    return render_template("inicio.html")

# ================= HOME =================
@app.route("/home")
@login_required
def index():
    solicitud_activa = Solicitud.query.filter_by(
        usuario_id=current_user.id_usuario,
        estado="En revisión"
    ).first()

    subsidios = db.session.execute(
        db.text("SELECT codigo_subsidio, nombre_programa FROM subsidio")
    ).fetchall()

    return render_template(
        "index.html",
        productos=obtener_productos(),
        solicitud_activa=solicitud_activa,
        subsidios=subsidios
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
    estado = request.args.get("estado")

    if estado:
        solicitudes = Solicitud.query.filter_by(estado=estado).all()
    else:
        solicitudes = Solicitud.query.all()

    # 🔥 FUNCIÓN SEGURA PARA CALCULAR VALOR
    def calcular_valor(s):
        if s.producto and s.producto.subsidio is not None:
            return round(s.producto.precio * (1 - s.producto.subsidio / 100), 2)
        return 0

    return render_template(
        "solicitudes.html",
        solicitudes=solicitudes,
        estado_actual=estado,
        calcular_valor=calcular_valor  # 👈 SE ENVÍA AL HTML
    )


# ================= MIS SOLICITUDES =================
@app.route("/mis_solicitudes")
@login_required
def mis_solicitudes():
    solicitudes = Solicitud.query.filter_by(
        usuario_id=current_user.id_usuario
    ).all()

    total_pagado = 0

    for s in solicitudes:
        if (
            s.estado == "Aprobado"
            and s.producto
            and s.producto.subsidio is not None
        ):
            total_pagado += s.producto.precio * (1 - s.producto.subsidio / 100)

    return render_template(
        "mis_solicitudes.html",
        solicitudes=solicitudes,
        total_pagado=round(total_pagado, 2)
    )
# ================= FORMULARIO EVALUACIÓN =================
@app.route("/formulario_evaluacion/<int:id_solicitud>", methods=["GET", "POST"])
@login_required
@admin_required
def formulario_evaluacion(id_solicitud):

    solicitud = db.session.get(Solicitud, id_solicitud)

    if not solicitud:
        flash("Solicitud no encontrada", "danger")
        return redirect(url_for("listar_solicitudes"))

    if request.method == "POST":

        # 🔥 FUNCIÓN PARA SWITCHES
        def valor(nombre, puntos):
            return puntos if request.form.get(nombre) == "on" else 0

        # ================= CRITERIOS AUTOMÁTICOS =================
        cedula_vigente = valor("cedula_vigente", 30)
        firma_documentos = valor("firma_documentos", 20)
        documentos_completos = valor("documentos_completos", 25)
        historial = valor("historial", 15)
        ubicacion = valor("ubicacion", 10)

        observaciones = request.form.get("observaciones")

        # 🔐 FIRMA DIGITAL (CORREGIDA)
        import hashlib

        fecha = datetime.now()  # 🔥 MISMA FECHA PARA TODO

        cadena = f"{current_user.id_usuario}-{id_solicitud}-{fecha}"
        firma = hashlib.sha256(cadena.encode()).hexdigest()

        # 🧾 Crear evaluación
        nueva_eval = Evaluacion(
            observaciones=observaciones,
            resultado="EN PROCESO",
            id_solicitud=id_solicitud,
            evaluado_por=current_user.id_usuario,
            fecha_evaluacion=fecha,  # 🔥 USAR MISMA FECHA
            firma_digital=firma
        )

        db.session.add(nueva_eval)
        db.session.commit()

        total = 0

        # ================= CRITERIOS AUTOMÁTICOS =================
        criterios_auto = [
            ("Cédula vigente", "Validación de cédula", cedula_vigente),
            ("Firma documentos", "Documentos firmados", firma_documentos),
            ("Documentos completos", "Entrega completa", documentos_completos),
            ("Historial crediticio", "Evaluación financiera", historial),
            ("Ubicación", "Verificación geográfica", ubicacion)
        ]

        for nombre, desc, puntaje in criterios_auto:
            nuevo = CriterioEvaluacion(
                id_evaluacion=nueva_eval.id_evaluacion,
                criterio=nombre,
                descripcion=desc,
                puntaje=puntaje
            )
            db.session.add(nuevo)
            total += puntaje

        # ================= CRITERIOS MANUALES =================
        criterios = request.form.getlist("criterio[]")
        descripciones = request.form.getlist("descripcion[]")
        puntajes = request.form.getlist("puntaje[]")

        for c, d, p in zip(criterios, descripciones, puntajes):
            if c and p:
                p = float(p)
                nuevo = CriterioEvaluacion(
                    id_evaluacion=nueva_eval.id_evaluacion,
                    criterio=c,
                    descripcion=d,
                    puntaje=p
                )
                db.session.add(nuevo)
                total += p

        # ================= RESULTADO =================
        nueva_eval.puntaje_total = total

        if total >= 70:
            nueva_eval.resultado = "APROBADO"
        elif total >= 40:
            nueva_eval.resultado = "EN PROCESO"
        else:
            nueva_eval.resultado = "RECHAZADO"

        db.session.commit()

        flash(f"Evaluación registrada correctamente (Puntaje: {total})", "success")
        return redirect(url_for("listar_solicitudes"))

    return render_template("formulario_evaluacion.html", solicitud=solicitud)
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
        if nuevo_estado == "Aprobado" and solicitud.estado != "Aprobado":
            producto = solicitud.producto

            if producto.cantidad > 0:
                producto.cantidad -= 1
            else:
                flash("No hay stock disponible", "danger")
                return redirect(url_for("listar_solicitudes"))

        solicitud.estado = nuevo_estado
        db.session.commit()

        flash(f"Estado cambiado a {nuevo_estado}", "success")
    else:
        flash("Solicitud no encontrada", "danger")

    return redirect(url_for("listar_solicitudes"))
# ================= APROBACIÓN AUTOMÁTICA =================
@app.route("/evaluar_solicitud/<int:id>")
@login_required
@admin_required
def evaluar_solicitud(id):

    solicitud = db.session.get(Solicitud, id)

    if not solicitud:
        flash("Solicitud no encontrada", "danger")
        return redirect(url_for("listar_solicitudes"))

    # 🔎 Obtener evaluación
    evaluacion = db.session.execute(
        db.text("""
            SELECT puntaje_total
            FROM evaluacion
            WHERE id_solicitud = :id
        """),
        {"id": id}
    ).fetchone()

    if not evaluacion:
        flash("No existe evaluación para esta solicitud", "warning")
        return redirect(url_for("listar_solicitudes"))

    puntaje = evaluacion[0]

    # 🤖 LÓGICA AUTOMÁTICA
    if puntaje >= 80:
        nuevo_estado = "Aprobado"

        # 📦 Descontar stock
        if solicitud.producto and solicitud.producto.cantidad > 0:
            solicitud.producto.cantidad -= 1
        else:
            flash("No hay stock disponible", "danger")
            return redirect(url_for("listar_solicitudes"))

    else:
        nuevo_estado = "Rechazado"

    solicitud.estado = nuevo_estado
    db.session.commit()

    flash(f"Solicitud evaluada automáticamente: {nuevo_estado} (Puntaje: {puntaje})", "success")
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

# ================= EDITAR PRODUCTO =================
@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def editar_producto(id):
    producto = db.session.get(ProductoDB, id)

    if not producto:
        flash("Producto no encontrado", "danger")
        return redirect(url_for("mostrar_inventario"))

    if request.method == "POST":
        producto.nombre = request.form.get("nombre")
        producto.precio = request.form.get("precio", type=float)
        producto.subsidio = request.form.get("subsidio", type=int)
        producto.cantidad = request.form.get("cantidad", type=int)

        db.session.commit()
        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("mostrar_inventario"))

    return render_template("editar_producto.html", producto=producto)

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

#  FIX ERROR
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

    data = [["Producto", "Cédula", "Sexo", "Valor", "Fecha", "Estado"]]

    for s in solicitudes:
        productor = db.session.execute(
            db.text("""
                SELECT sexo
                FROM productores
                WHERE cedula = :cedula
            """),
            {"cedula": s.cedula}
        ).fetchone()

        sexo = productor[0] if productor else ""

        valor = 0
        if s.producto:
            valor = s.producto.precio * (1 - s.producto.subsidio / 100)

        data.append([
            s.producto.nombre if s.producto else "",
            s.cedula,
            sexo,
            round(valor, 2),
            s.fecha.strftime("%Y-%m-%d") if s.fecha else "",
            s.estado
        ])

    doc.build([Table(data)])
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="solicitudes_sexo.pdf", mimetype="application/pdf")

# ================= REPORTE PROVINCIA =================
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

@app.route("/reporte_provincia_pdf")
@login_required
def reporte_provincia_pdf():
    provincia = request.args.get("provincia")
    cedula = request.args.get("cedula")

    query = """
        SELECT s.cedula, p.provincia, pr.nombre, s.fecha, s.estado
        FROM solicitudes s
        JOIN productores p ON s.cedula = p.cedula
        JOIN productos pr ON s.producto_id = pr.id
        WHERE 1=1
    """

    params = {}

    if provincia:
        query += " AND p.provincia = :provincia"
        params["provincia"] = provincia

    if cedula:
        query += " AND s.cedula = :cedula"
        params["cedula"] = cedula

    solicitudes = db.session.execute(db.text(query), params).fetchall()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elementos = []

    # 🧾 ENCABEZADO
    elementos.append(Paragraph("REPORTE DE SOLICITUDES", styles["Title"]))
    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(f"Provincia: {provincia or 'Todas'}", styles["Normal"]))
    elementos.append(Paragraph(f"Cédula: {cedula or 'Todas'}", styles["Normal"]))
    elementos.append(Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    elementos.append(Spacer(1, 15))

    # 📊 TABLA
    data = [["Producto", "Cédula", "Provincia", "Fecha", "Estado"]]

    for s in solicitudes:
        data.append([
            s[2],
            s[0],
            s[1],
            s[3].strftime("%Y-%m-%d"),
            s[4]
        ])

    tabla = Table(data)

    # 🎨 ESTILO PROFESIONAL
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))

    elementos.append(tabla)

    doc.build(elementos)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="reporte_filtrado.pdf",
        mimetype="application/pdf"
    )
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

# ================= BUSCAR =================
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
# ================= REPORTES =================
@app.route("/reportes")
@login_required
@admin_required
def reportes():
    por_provincia = db.session.execute(db.text("""
        SELECT p.provincia, COUNT(*) as total
        FROM solicitudes s
        JOIN productores p ON s.cedula = p.cedula
        GROUP BY p.provincia
    """)).fetchall()

    por_sexo = db.session.execute(db.text("""
        SELECT p.sexo, COUNT(*) as total
        FROM solicitudes s
        JOIN productores p ON s.cedula = p.cedula
        GROUP BY p.sexo
    """)).fetchall()

    por_producto = db.session.execute(db.text("""
        SELECT pr.nombre, COUNT(*) as total
        FROM solicitudes s
        JOIN productos pr ON s.producto_id = pr.id
        GROUP BY pr.nombre
    """)).fetchall()

    return render_template(
        "reportes.html",
        por_provincia=por_provincia,
        por_sexo=por_sexo,
        por_producto=por_producto
    )
# ================= FILTRO POR SUBSIDIO =================
@app.route("/obtener_productos_por_subsidio")
@login_required
def obtener_productos_por_subsidio():
    codigo = request.args.get("codigo")

    productos = db.session.execute(
        db.text("""
            SELECT id, nombre
            FROM productos
            WHERE codigo_subsidio = :codigo
        """),
        {"codigo": codigo}
    ).fetchall()

    return jsonify([
        {"id": p[0], "nombre": p[1]} for p in productos
    ])


# ================= DETALLE BENEFICIARIO =================
@app.route("/detalle_beneficiario/<cedula>/<int:id_solicitud>")
@login_required
@admin_required
def detalle_beneficiario(cedula, id_solicitud):

    # 🔎 DATOS DEL PRODUCTOR
    productor = db.session.execute(
        db.text("""
            SELECT nombres, apellidos, provincia, canton, parroquia, sexo
            FROM productores
            WHERE cedula = :cedula
        """),
        {"cedula": cedula}
    ).fetchone()

    # 📊 DATOS DE EVALUACIÓN (AHORA INCLUYE FIRMA)
    evaluacion = db.session.execute(
        db.text("""
            SELECT id_evaluacion, observaciones, puntaje_total, resultado, firma_digital
            FROM evaluacion
            WHERE id_solicitud = :id
        """),
        {"id": id_solicitud}
    ).fetchone()

    criterios = []
    qr_base64 = None  # 🔥 VARIABLE PARA EL QR

    if evaluacion:

        # 🔐 GENERAR QR CON LA FIRMA
        qr = qrcode.make(evaluacion[4])
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        # 📊 CRITERIOS
        criterios = db.session.execute(
            db.text("""
                SELECT criterio, descripcion, puntaje
                FROM criterio_evaluacion
                WHERE id_evaluacion = :id_eval
            """),
            {"id_eval": evaluacion[0]}
        ).fetchall()

    return render_template(
        "detalle_beneficiario.html",
        productor=productor,
        evaluacion=evaluacion,
        criterios=criterios,
        qr_base64=qr_base64  # 🔥 SE ENVÍA AL HTML
    )
# ================= VERIFICAR FIRMA =================
@app.route("/verificar_firma/<firma>")
@login_required
def verificar_firma(firma):

    evaluacion = db.session.execute(
        db.text("""
            SELECT e.id_evaluacion, e.resultado, e.puntaje_total,
                   s.cedula, u.nombre
            FROM evaluacion e
            JOIN solicitudes s ON e.id_solicitud = s.id_solicitud
            JOIN usuarios u ON e.evaluado_por = u.id_usuario
            WHERE e.firma_digital = :firma
        """),
        {"firma": firma}
    ).fetchone()

    if not evaluacion:
        return "<h2 style='color:red'>❌ Firma inválida o alterada</h2>"

    return f"""
    <h2 style='color:green'>✅ Firma válida</h2>
    <p><strong>Evaluador:</strong> {evaluacion[4]}</p>
    <p><strong>Cédula:</strong> {evaluacion[3]}</p>
    <p><strong>Puntaje:</strong> {evaluacion[2]}</p>
    <p><strong>Resultado:</strong> {evaluacion[1]}</p>
    """
# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
