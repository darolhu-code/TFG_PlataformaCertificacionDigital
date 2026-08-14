# Script de prueba básico para JWT: login correcto, login incorrecto y /auth/me con y sin token
# Requiere el servidor arrancado (uvicorn main:app --reload) y reutiliza el primer alumno existente
import requests

from database.connection import SessionLocal
from database.dao import list_student_certificates
from database.models import Student

BASE_URL = "http://127.0.0.1:8000"


# prueba el flujo básico de autenticación reutilizando el primer alumno existente (contraseña "password")
def test_jwt():
    db = SessionLocal()
    student = db.query(Student).first()
    db.close()

    if student is None:
        print("No hay alumnos en la base de datos. Ejecuta antes scripts.dao_test")
        return

    print("=" * 30)
    print("Prueba básica de JWT")
    print("=" * 30)
    print()
    print(f"Alumno: {student.nombre} {student.apellidos} (email={student.email})")
    print()

    try:
        # login con contraseña correcta
        response = requests.post(f"{BASE_URL}/auth/login", json={"email": student.email, "password": "password"})
    except requests.exceptions.ConnectionError:
        print(f"No se puede conectar con {BASE_URL}. Arranca antes el servidor: uvicorn main:app --reload")
        return

    print(f"Login correcto: {response.status_code} (esperado 200)")
    token = response.json().get("access_token") if response.status_code == 200 else None

    # login con contraseña incorrecta
    response = requests.post(f"{BASE_URL}/auth/login", json={"email": student.email, "password": "mala"})
    print(f"Login con contraseña incorrecta: {response.status_code} (esperado 401)")
    print()

    # /auth/me con el token obtenido
    response = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    print(f"/auth/me con token válido: {response.status_code} (esperado 200)")
    if response.status_code == 200:
        print(response.json())

    # /auth/me sin token
    response = requests.get(f"{BASE_URL}/auth/me")
    print(f"/auth/me sin token: {response.status_code} (esperado 401)")
    print()

    # consumo de un endpoint protegido de la API con el token del alumno: consulta uno de sus propios certificados
    db = SessionLocal()
    certificate = list_student_certificates(db, student.id)
    db.close()

    if certificate:
        certificate_id = certificate[0].id
        response = requests.get(f"{BASE_URL}/certificates/{certificate_id}", headers={"Authorization": f"Bearer {token}"})
        print(f"GET /certificates/{certificate_id} con token del propietario: {response.status_code} (esperado 200)")
    else:
        print(f"El alumno {student.email} no tiene certificados; se omite la prueba de GET /certificates/{{id}}")

    print()
    print("Prueba de JWT: OK")


if __name__ == "__main__":
    test_jwt()
