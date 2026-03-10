import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:

    SECRET_KEY = os.environ.get("SECRET_KEY", "magp_secret")

    # Si existe DATABASE_URL (Render), usa PostgreSQL
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:

        # Corrección para PostgreSQL en Render
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        SQLALCHEMY_DATABASE_URI = DATABASE_URL

    else:
        # Base de datos local MySQL
        SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:Miguel2018@localhost/sistema_magp"

    SQLALCHEMY_TRACK_MODIFICATIONS = False