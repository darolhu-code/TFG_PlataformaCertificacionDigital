# Script de prueba para comprobar la conexión con la base de datos PostgreSQL (Supabase)
from sqlalchemy import text
from database.connection import engine

# comprueba que la conexión con PostgreSQL (Supabase) funciona correctamente
def comprobar_conexion():
    with engine.connect() as connection:
        resultado = connection.execute(text("SELECT 1")).scalar()

    print(f"Conexión con PostgreSQL correcta: {resultado}")


if __name__ == "__main__":
    comprobar_conexion()
