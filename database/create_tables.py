# Script para crear las tablas en la base de datos PostgreSQL utilizando SQLAlchemy y los modelos definidos en database/models.py
# Este script se ejecuta una sola vez para inicializar la base de datos y crear las tablas necesarias.
from database.connection import Base, engine
from database import models 

# crea en PostgreSQL todas las tablas definidas en database/models.py
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente")


if __name__ == "__main__":
    create_tables()
