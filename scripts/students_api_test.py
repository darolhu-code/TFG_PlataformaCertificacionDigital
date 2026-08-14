# Prueba de la API de gestión de alumnos (crear/listar/consultar).
# Requiere el servidor arrancado (uvicorn main:app --reload).
import uuid
import requests

from auth.security import ActorType, create_access_token
from database.connection import SessionLocal
from database.models import Student

BASE_URL = "http://127.0.0.1:8000"

# Actores ya existentes en la base de datos, reutilizados para generar el JWT sin pasar por login.
ADMIN_ID = 1
ORG_ID = 1
STUDENT_ID = 1


def check(label, condition):
    print(f"{'OK   ' if condition else 'FALLO'} {label}")


def nuevo_alumno(sufijo):
    # dni es VARCHAR(20) en la base de datos: el sufijo debe ser corto para no superar el límite.
    return {
        "dni": f"D{sufijo}",
        "nombre": "Alumno",
        "apellidos": "De prueba",
        "email": f"alumno_demo_{sufijo}@test.com",
        "password": "password123",
    }


def test_students_api():
    admin = {"Authorization": f"Bearer {create_access_token(ADMIN_ID, ActorType.ADMINISTRATOR)}"}
    organization = {"Authorization": f"Bearer {create_access_token(ORG_ID, ActorType.ORGANIZATION)}"}
    student = {"Authorization": f"Bearer {create_access_token(STUDENT_ID, ActorType.STUDENT)}"}

    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print(f"No se puede conectar con {BASE_URL}. Arranca antes el servidor: uvicorn main:app --reload")
        return

    creados_ids = []
    sufijo = uuid.uuid4().hex[:8]

    # --- Crear alumno como ADMINISTRATOR ---
    datos_admin = nuevo_alumno(f"admin-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/students", json=datos_admin, headers=admin)
    creado_correctamente = respuesta.status_code == 201
    check(f"crear como ADMINISTRATOR -> {respuesta.status_code} (esperado 201)", creado_correctamente)
    if creado_correctamente:
        # Guardamos el id para poder consultarlo más abajo y borrarlo al final.
        alumno_creado_id = respuesta.json()["student_id"]
        creados_ids.append(alumno_creado_id)

    # --- Crear alumno como ORGANIZATION ---
    datos_org = nuevo_alumno(f"org-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/students", json=datos_org, headers=organization)
    check(f"crear como ORGANIZATION -> {respuesta.status_code} (esperado 201)", respuesta.status_code == 201)
    if respuesta.status_code == 201:
        creados_ids.append(respuesta.json()["student_id"])

    # --- Un alumno no puede crear otros alumnos ---
    datos_student = nuevo_alumno(f"student-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/students", json=datos_student, headers=student)
    check(f"crear como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- DNI y email duplicados: reutilizamos los mismos datos del primer alumno creado ---
    respuesta = requests.post(f"{BASE_URL}/students", json=datos_admin, headers=admin)
    check(f"DNI y email duplicados -> {respuesta.status_code} (esperado 400)", respuesta.status_code == 400)

    # --- Crear sin enviar ningún token ---
    datos_sin_jwt = nuevo_alumno(f"sinjwt-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/students", json=datos_sin_jwt)
    check(f"crear sin JWT -> {respuesta.status_code} (esperado 401)", respuesta.status_code == 401)

    # --- Listado: administrador y organización sí pueden, alumno no ---
    respuesta = requests.get(f"{BASE_URL}/students", headers=admin)
    listado_cargado_correctamente = respuesta.status_code == 200
    if listado_cargado_correctamente:
        total_alumnos = len(respuesta.json())
    else:
        total_alumnos = "-"
    check(f"listado como ADMINISTRATOR -> {respuesta.status_code} (esperado 200), total={total_alumnos}", listado_cargado_correctamente)

    respuesta = requests.get(f"{BASE_URL}/students", headers=organization)
    check(f"listado como ORGANIZATION -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    respuesta = requests.get(f"{BASE_URL}/students", headers=student)
    check(f"listado como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Consulta del alumno que hemos creado como ADMINISTRATOR ---
    if creados_ids:
        primer_alumno_id = creados_ids[0]
        respuesta = requests.get(f"{BASE_URL}/students/{primer_alumno_id}", headers=admin)
        check(f"consultar alumno creado -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)
        check("respuesta sin password_hash", "password_hash" not in respuesta.json())

    # --- Consulta de un alumno que no existe ---
    respuesta = requests.get(f"{BASE_URL}/students/999999", headers=admin)
    check(f"consultar alumno inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # Limpieza: se eliminan los alumnos creados durante la prueba
    if creados_ids:
        db = SessionLocal()
        for student_id in creados_ids:
            alumno = db.get(Student, student_id)
            if alumno is not None:
                db.delete(alumno)
        db.commit()
        db.close()
        print(f"Alumnos de prueba eliminados: {creados_ids}")


if __name__ == "__main__":
    test_students_api()
