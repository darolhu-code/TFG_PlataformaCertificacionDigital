# Prueba de la API de gestión de organizaciones (crear/listar/consultar).
# Requiere el servidor arrancado (uvicorn main:app --reload).
import uuid
import requests

from auth.security import ActorType, create_access_token
from database.connection import SessionLocal
from database.models import Organization

BASE_URL = "http://127.0.0.1:8000"

# Actores ya existentes en la base de datos, reutilizados para generar el JWT sin pasar por login.
ADMIN_ID = 1
ORG_ID = 1
STUDENT_ID = 1


def check(label, condition):
    print(f"{'OK   ' if condition else 'FALLO'} {label}")


def nueva_organizacion(sufijo):
    return {
        "nombre": "Organización de prueba",
        "tipo": "Empresa",
        "email": f"organizacion_demo_{sufijo}@test.com",
        "password": "password123",
    }


def test_organizations_api():
    admin = {"Authorization": f"Bearer {create_access_token(ADMIN_ID, ActorType.ADMINISTRATOR)}"}
    organization = {"Authorization": f"Bearer {create_access_token(ORG_ID, ActorType.ORGANIZATION)}"}
    student = {"Authorization": f"Bearer {create_access_token(STUDENT_ID, ActorType.STUDENT)}"}

    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print(f"No se puede conectar con {BASE_URL}. Arranca antes el servidor: uvicorn main:app --reload")
        return

    creadas_ids = []
    sufijo = uuid.uuid4().hex[:8]

    # --- Crear organización como ADMINISTRATOR ---
    datos_admin = nueva_organizacion(f"admin-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/organizations", json=datos_admin, headers=admin)
    creada_correctamente = respuesta.status_code == 201
    check(f"crear como ADMINISTRATOR -> {respuesta.status_code} (esperado 201)", creada_correctamente)
    if creada_correctamente:
        # Guardamos el id para poder consultarlo más abajo y borrarlo al final.
        organizacion_creada_id = respuesta.json()["organization_id"]
        creadas_ids.append(organizacion_creada_id)
        check("respuesta sin password_hash", "password_hash" not in respuesta.json())

    # --- Email duplicado: reutilizamos los mismos datos de la primera organización creada ---
    respuesta = requests.post(f"{BASE_URL}/organizations", json=datos_admin, headers=admin)
    check(f"email duplicado -> {respuesta.status_code} (esperado 400)", respuesta.status_code == 400)

    # --- Crear sin enviar ningún token ---
    datos_sin_jwt = nueva_organizacion(f"sinjwt-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/organizations", json=datos_sin_jwt)
    check(f"crear sin JWT -> {respuesta.status_code} (esperado 401)", respuesta.status_code == 401)

    # --- Una organización no puede crear otras organizaciones ---
    datos_org = nueva_organizacion(f"org-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/organizations", json=datos_org, headers=organization)
    check(f"crear como ORGANIZATION -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Un alumno no puede crear organizaciones ---
    datos_student = nueva_organizacion(f"student-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/organizations", json=datos_student, headers=student)
    check(f"crear como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Consulta de la organización que hemos creado ---
    if creadas_ids:
        primera_organizacion_id = creadas_ids[0]
        respuesta = requests.get(f"{BASE_URL}/organizations/{primera_organizacion_id}", headers=admin)
        check(f"consultar organización creada -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    # --- Consulta de una organización que no existe ---
    respuesta = requests.get(f"{BASE_URL}/organizations/999999", headers=admin)
    check(f"consultar organización inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- GET /organizations (accesible a cualquier actor autenticado) ---
    respuesta = requests.get(f"{BASE_URL}/organizations", headers=student)
    listado_cargado_correctamente = respuesta.status_code == 200
    if listado_cargado_correctamente:
        total_organizaciones = len(respuesta.json())
    else:
        total_organizaciones = "-"
    check(f"GET /organizations -> {respuesta.status_code} (esperado 200), total={total_organizaciones}", listado_cargado_correctamente)

    # --- GET /organizations/{id}/certificates ---
    respuesta = requests.get(f"{BASE_URL}/organizations/{ORG_ID}/certificates", headers=organization)
    check(f"GET /organizations/{{id}}/certificates -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    # Limpieza: se eliminan las organizaciones creadas durante la prueba
    if creadas_ids:
        db = SessionLocal()
        for organization_id in creadas_ids:
            org = db.get(Organization, organization_id)
            if org is not None:
                db.delete(org)
        db.commit()
        db.close()
        print(f"Organizaciones de prueba eliminadas: {creadas_ids}")


if __name__ == "__main__":
    test_organizations_api()
