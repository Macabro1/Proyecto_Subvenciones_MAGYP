import mysql.connector

def obtener_conexion():
    
    conexion = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sistema_magp"
    )

    return conexion