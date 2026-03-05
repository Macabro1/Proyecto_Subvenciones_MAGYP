import os
import json
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Crear carpeta data si no existe
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

TXT_FILE = os.path.join(DATA_DIR, "datos.txt")
JSON_FILE = os.path.join(DATA_DIR, "datos.json")
CSV_FILE = os.path.join(DATA_DIR, "datos.csv")


# ===============================
# GUARDAR EN TXT
# ===============================
def guardar_txt(nombre, cedula):
    with open(TXT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{nombre},{cedula}\n")


def leer_txt():
    datos = []
    if os.path.exists(TXT_FILE):
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            for linea in f:
                partes = linea.strip().split(",")
                if len(partes) == 2:
                    datos.append({
                        "nombre": partes[0],
                        "cedula": partes[1]
                    })
    return datos


# ===============================
# GUARDAR EN JSON
# ===============================
def guardar_json(nombre, cedula):

    datos = []

    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                datos = json.load(f)
            except:
                datos = []

    datos.append({
        "nombre": nombre,
        "cedula": cedula
    })

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)


def leer_json():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []


# ===============================
# GUARDAR EN CSV (con encabezado automático)
# ===============================
def guardar_csv(nombre, cedula):

    file_exists = os.path.exists(CSV_FILE)
    file_empty = not file_exists or os.path.getsize(CSV_FILE) == 0

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if file_empty:
            writer.writerow(["nombre", "cedula"])

        writer.writerow([nombre, cedula])


def leer_csv():

    datos = []

    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for fila in reader:
                if len(fila) == 2 and fila[0] != "nombre":
                    datos.append({
                        "nombre": fila[0],
                        "cedula": fila[1]
                    })

    return datos


# ===============================
# LIMPIAR ARCHIVOS
# ===============================
def limpiar_archivos():

    for archivo in [TXT_FILE, JSON_FILE, CSV_FILE]:
        if os.path.exists(archivo):
            os.remove(archivo)