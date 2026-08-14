# Prueba de la API de gestión de cursos: crear, consultar, listar y ver los alumnos matriculados de un curso.
# Requiere el servidor arrancado (uvicorn main:app --reload).
import uuid
import requests

from auth.security import ActorType, create_access_token
from database.connection import SessionLocal
from database.models import Course

BASE_URL = "http://127.0.0.1:8000"

# Actores ya existentes en la base de datos, reutilizados para generar el JWT sin pasar por login.
ADMIN_ID = 1
ORG1_ID = 1
ORG2_ID = 2
STUDENT_ID = 1


def check(label, condition):
    print(f"{'OK   ' if condition else 'FALLO'} {label}")


def nuevo_curso(organization_id, sufijo):
    return {
        "organization_id": organization_id,
        "course_name": f"Curso de prueba {sufijo}",
        "description": "Curso creado por el script de pruebas",
        "teacher": "Docente de prueba",
        "hours": 10,
    }


def test_courses_api():
    admin = {"Authorization": f"Bearer {create_access_token(ADMIN_ID, ActorType.ADMINISTRATOR)}"}
    organization1 = {"Authorization": f"Bearer {create_access_token(ORG1_ID, ActorType.ORGANIZATION)}"}
    student = {"Authorization": f"Bearer {create_access_token(STUDENT_ID, ActorType.STUDENT)}"}

    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print(f"No se puede conectar con {BASE_URL}. Arranca antes el servidor: uvicorn main:app --reload")
        return

    creados_ids = []
    sufijo = uuid.uuid4().hex[:8]

    # --- Crear curso como ADMINISTRATOR (para la organización 1) ---
    datos_admin = nuevo_curso(ORG1_ID, f"admin-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/courses", json=datos_admin, headers=admin)
    creado_correctamente = respuesta.status_code == 201
    check(f"crear como ADMINISTRATOR -> {respuesta.status_code} (esperado 201)", creado_correctamente)
    if creado_correctamente:
        # Guardamos el id para poder consultarlo más abajo y borrarlo al final.
        curso_creado_id = respuesta.json()["course_id"]
        creados_ids.append(curso_creado_id)

    # --- Crear curso como ORGANIZATION para sí misma ---
    datos_org = nuevo_curso(ORG1_ID, f"org-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/courses", json=datos_org, headers=organization1)
    check(f"crear como ORGANIZATION para sí misma -> {respuesta.status_code} (esperado 201)", respuesta.status_code == 201)
    if respuesta.status_code == 201:
        creados_ids.append(respuesta.json()["course_id"])

    # --- Una organización no puede crear cursos para otra organización ---
    datos_otra_org = nuevo_curso(ORG2_ID, f"otraorg-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/courses", json=datos_otra_org, headers=organization1)
    check(f"crear para otra organización -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Organización inexistente ---
    datos_org_inexistente = nuevo_curso(999999, f"orginexistente-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/courses", json=datos_org_inexistente, headers=admin)
    check(f"organización inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- Crear sin enviar ningún token ---
    datos_sin_jwt = nuevo_curso(ORG1_ID, f"sinjwt-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/courses", json=datos_sin_jwt)
    check(f"crear sin JWT -> {respuesta.status_code} (esperado 401)", respuesta.status_code == 401)

    # --- Un alumno no puede crear cursos ---
    datos_student = nuevo_curso(ORG1_ID, f"student-{sufijo}")
    respuesta = requests.post(f"{BASE_URL}/courses", json=datos_student, headers=student)
    check(f"crear como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Consulta del curso que hemos creado ---
    if creados_ids:
        primer_curso_id = creados_ids[0]
        respuesta = requests.get(f"{BASE_URL}/courses/{primer_curso_id}", headers=admin)
        check(f"consultar curso creado -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

        respuesta = requests.get(f"{BASE_URL}/courses/{primer_curso_id}", headers=student)
        check(f"consultar curso como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Consulta de un curso que no existe ---
    respuesta = requests.get(f"{BASE_URL}/courses/999999", headers=admin)
    check(f"consultar curso inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- GET /courses (listado) ---
    respuesta = requests.get(f"{BASE_URL}/courses", headers=admin)
    listado_cargado_correctamente = respuesta.status_code == 200
    if listado_cargado_correctamente:
        total_cursos = len(respuesta.json())
    else:
        total_cursos = "-"
    check(f"GET /courses sigue funcionando -> {respuesta.status_code} (esperado 200), total={total_cursos}", listado_cargado_correctamente)

    respuesta = requests.get(f"{BASE_URL}/courses", headers=student)
    check(f"GET /courses como STUDENT sigue devolviendo 403 -> {respuesta.status_code}", respuesta.status_code == 403)

    # --- GET /courses/{id}/students ---
    respuesta = requests.get(f"{BASE_URL}/courses/{ORG1_ID}/students", headers=organization1)
    check(f"GET /courses/{{id}}/students sigue funcionando -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    # Limpieza: se eliminan los cursos creados durante la prueba
    if creados_ids:
        db = SessionLocal()
        for course_id in creados_ids:
            curso = db.get(Course, course_id)
            if curso is not None:
                db.delete(curso)
        db.commit()
        db.close()
        print(f"Cursos de prueba eliminados: {creados_ids}")


if __name__ == "__main__":
    test_courses_api()
