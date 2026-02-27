class Producto:

    def __init__(self, id, nombre, precio, subsidio, cantidad):
        self.id = id
        self.nombre = nombre
        self.precio = precio
        self.subsidio = subsidio
        self.cantidad = cantidad

    def actualizar_cantidad(self, nueva_cantidad):
        self.cantidad = nueva_cantidad

    def actualizar_precio(self, nuevo_precio):
        self.precio = nuevo_precio

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "precio": self.precio,
            "subsidio": self.subsidio,
            "cantidad": self.cantidad
        }


class Inventario:

    def __init__(self):
        # 🔥 Colección principal (diccionario)
        self.productos = {}

    def cargar_desde_db(self, lista_productos):
        for p in lista_productos:
            producto = Producto(
                p.id, p.nombre, p.precio, p.subsidio, p.cantidad
            )
            self.productos[p.id] = producto

    def agregar_producto(self, producto):
        self.productos[producto.id] = producto

    def eliminar_producto(self, id_producto):
        if id_producto in self.productos:
            del self.productos[id_producto]

    def buscar_por_nombre(self, nombre):
        return [
            p for p in self.productos.values()
            if nombre.lower() in p.nombre.lower()
        ]

    def mostrar_todos(self):
        return list(self.productos.values())