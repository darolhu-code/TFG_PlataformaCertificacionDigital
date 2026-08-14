import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

# Motor de conexión con PostgreSQL (Supabase)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Fábrica de sesiones para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base de la que heredarán los futuros modelos de SQLAlchemy
Base = declarative_base()

# Proporciona una sesión de base de datos y la cierra correctamente al finalizar
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
