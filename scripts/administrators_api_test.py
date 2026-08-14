# Prueba de la API de gestión de administradores (crear/listar/consultar).
# Requiere el servidor arrancado (uvicorn main:app --reload).
import uuid
import requests

from auth.security import ActorType, create_access_token
from database.connection import SessionLocal
from database.models import Administrator

BASE_URL = "http://127.0.0.1:8000"

# Actores ya existentes en la base de datos, reutilizados para generar el JWT sin pasar por login.
ADMIN_ID = 1
ORG_ID = 1
STUDENT_ID = 1


def check(label, condition):
    print(f"{'OK   ' if condition else 'FALLO'} {label}")


def nuevo_administrador(sufijo):
    # dni es VARCHAR(20) en la base de datos: el sufijo debe ser corto para no superar el límite.
    return {
        "dni": f"A{sufijo}",
        "nombre": "Admin",
        "apellidos": "De prueba",
        "email": f"admin_demo_{sufijo}@test.com",
        "password": "password123",
    }


def test_administrators_api():
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

    # --- Crear administrador como ADMINISTRATOR ---
    datos_admin = nuevo_administrador(sufijo)
    respuesta = requests.post(f"{BASE_URL}/administrators", json=datos_admin, headers=admin)
    creado_correctamente = respuesta.status_code == 201
    check(f"crear como ADMINISTRATOR -> {respuesta.status_code} (esperado 201)", creado_correctamente)
    if creado_correctamente:
        # Guardamos el id para poder consultarlo más abajo y borrarlo al final.
        administrador_creado_id = respuesta.json()["administrator_id"]
        creados_ids.append(administrador_creado_id)
        check("respuesta sin password_hash", "password_hash" not in respuesta.json())

    # --- DNI y email duplicados: reutilizamos los mismos datos del administrador ya creado ---
    respuesta = requests.post(f"{BASE_URL}/administrators", json=datos_admin, headers=admin)
    check(f"DNI y email duplicados -> {respuesta.status_code} (esperado 400)", respuesta.status_code == 400)

    # --- Crear sin enviar ningún token ---
    datos_sin_jwt = nuevo_administrador(f"sinjwt-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/administrators", json=datos_sin_jwt)
    check(f"crear sin JWT -> {respuesta.status_code} (esperado 401)", respuesta.status_code == 401)

    # --- Una organización no puede crear administradores ---
    datos_org = nuevo_administrador(f"org-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/administrators", json=datos_org, headers=organization)
    check(f"crear como ORGANIZATION -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Un alumno no puede crear administradores ---
    datos_student = nuevo_administrador(f"student-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/administrators", json=datos_student, headers=student)
    check(f"crear como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Listado: solo el administrador puede consultarlo ---
    respuesta = requests.get(f"{BASE_URL}/administrators", headers=admin)
    listado_cargado_correctamente = respuesta.status_code == 200
    if listado_cargado_correctamente:
        total_administradores = len(respuesta.json())
    else:
        total_administradores = "-"
    check(f"listado como ADMINISTRATOR -> {respuesta.status_code} (esperado 200), total={total_administradores}", listado_cargado_correctamente)

    respuesta = requests.get(f"{BASE_URL}/administrators", headers=organization)
    check(f"listado como ORGANIZATION -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    respuesta = requests.get(f"{BASE_URL}/administrators", headers=student)
    check(f"listado como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Consulta del administrador que hemos creado ---
    if creados_ids:
        primer_administrador_id = creados_ids[0]
        respuesta = requests.get(f"{BASE_URL}/administrators/{primer_administrador_id}", headers=admin)
        check(f"consultar administrador creado -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    # --- Consulta de un administrador que no existe ---
    respuesta = requests.get(f"{BASE_URL}/administrators/999999", headers=admin)
    check(f"consultar administrador inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- Login con el administrador recién creado ---
    respuesta = requests.post(f"{BASE_URL}/auth/login", json={"email": datos_admin["email"], "password": datos_admin["password"]})
    check(f"login con el administrador creado -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    # Limpieza: se eliminan los administradores creados durante la prueba
    if creados_ids:
        db = SessionLocal()
        for administrator_id in creados_ids:
            administrador = db.get(Administrator, administrator_id)
            if administrador is not None:
                db.delete(administrador)
        db.commit()
        db.close()
        print(f"Administradores de prueba eliminados: {creados_ids}")


if __name__ == "__main__":
    test_administrators_api()
