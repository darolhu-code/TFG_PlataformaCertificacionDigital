# Módulo principal de la aplicación FastAPI para la gestión de certificados digitales.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.administrators import router as administrators_router
from api.auth import router as auth_router
from api.certificates import router as certificates_router
from api.courses import router as courses_router
from api.organizations import router as organizations_router
from api.permissions import router as permissions_router
from api.students import router as students_router

# Creamos la instancia de FastAPI y registramos los routers de autenticación, certificados, alumnos, organizaciones, administradores, cursos y permisos
app = FastAPI()

# Permite que el frontend (servido desde localhost o desde el servicio desplegado en render) consuma la API.
# La autenticación va por token Bearer en la cabecera, no por cookies, así que no hace falta allow_credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://proyecto-tfg-84rd.onrender.com",
],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(certificates_router)
app.include_router(students_router)
app.include_router(organizations_router)
app.include_router(administrators_router)
app.include_router(courses_router)
app.include_router(permissions_router)

# Endpoint raíz para comprobar que la API está funcionando correctamente
@app.get("/")
def read_root():
    return {
        "status": "ok", 
        "message": "API funcionando"
    }
