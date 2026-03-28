class ProductoForm:

    def __init__(self, form):
        self.nombre = form.get("nombre")
        self.precio = form.get("precio")
        self.subsidio = form.get("subsidio")
        self.cantidad = form.get("cantidad")

    def validar(self):
        if not self.nombre or not self.precio or not self.subsidio or not self.cantidad:
            return False
        return True