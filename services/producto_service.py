from models import db, ProductoDB

# ===============================
# OBTENER TODOS
# ===============================
def obtener_productos():
    return ProductoDB.query.all()

# ===============================
# OBTENER POR ID
# ===============================
def obtener_producto(id):
    return ProductoDB.query.get_or_404(id)

# ===============================
# CREAR
# ===============================
def crear_producto(nombre, precio, subsidio, cantidad):

    nuevo = ProductoDB(
        nombre=nombre,
        precio=float(precio),
        subsidio=int(subsidio),
        cantidad=int(cantidad)
    )

    db.session.add(nuevo)
    db.session.commit()

# ===============================
# ACTUALIZAR
# ===============================
def actualizar_producto(id, nombre, precio, subsidio, cantidad):

    producto = ProductoDB.query.get_or_404(id)

    producto.nombre = nombre
    producto.precio = float(precio)
    producto.subsidio = int(subsidio)
    producto.cantidad = int(cantidad)

    db.session.commit()

# ===============================
# ELIMINAR
# ===============================
def eliminar_producto(id):

    producto = ProductoDB.query.get_or_404(id)

    db.session.delete(producto)
    db.session.commit()