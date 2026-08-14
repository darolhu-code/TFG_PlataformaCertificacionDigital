# Prueba de la API de gestión de matrículas (matricular/desmatricular), más GET /courses/{id}/students.
# Requiere el servidor arrancado (uvicorn main:app --reload).
from auth.security import ActorType, create_access_token
from database.connection import SessionLocal
from database.models import CourseEnrollment
import requests

BASE_URL = "http://127.0.0.1:8000"

# Actores y datos ya existentes en la base de datos, reutilizados para generar el JWT sin pasar por login.
ADMIN_ID = 1
ORG1_ID = 1          # AAPP1, dueña del curso 1
STUDENT_ID = 1
COURSE1_ID = 1       # pertenece a AAPP1
COURSE2_ID = 2       # pertenece a otra organización (AAPP2), para probar los 403
STUDENT_A_ID = 4     # alumno sin matricular en el curso 1 al empezar la prueba
STUDENT_B_ID = 5     # alumno sin matricular en el curso 1 al empezar la prueba


def check(label, condition):
    print(f"{'OK   ' if condition else 'FALLO'} {label}")


def esta_matriculado(db, student_id, course_id):
    fila = db.query(CourseEnrollment).filter_by(alumno_id=student_id, curso_id=course_id).first()
    return fila is not None


def test_enrollments_api():
    admin = {"Authorization": f"Bearer {create_access_token(ADMIN_ID, ActorType.ADMINISTRATOR)}"}
    organization1 = {"Authorization": f"Bearer {create_access_token(ORG1_ID, ActorType.ORGANIZATION)}"}
    student = {"Authorization": f"Bearer {create_access_token(STUDENT_ID, ActorType.STUDENT)}"}

    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print(f"No se puede conectar con {BASE_URL}. Arranca antes el servidor: uvicorn main:app --reload")
        return

    db = SessionLocal()
    if esta_matriculado(db, STUDENT_A_ID, COURSE1_ID) or esta_matriculado(db, STUDENT_B_ID, COURSE1_ID):
        print(f"Los alumnos {STUDENT_A_ID}/{STUDENT_B_ID} ya están matriculados en el curso {COURSE1_ID}: aborto para no dejar la prueba a medias.")
        db.close()
        return
    db.close()

    # --- Matricular alumno como ADMINISTRATOR ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE1_ID}/students", json={"student_id": STUDENT_A_ID}, headers=admin)
    check(f"matricular como ADMINISTRATOR -> {respuesta.status_code} (esperado 201)", respuesta.status_code == 201)

    # --- Matricular alumno como ORGANIZATION en un curso propio ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE1_ID}/students", json={"student_id": STUDENT_B_ID}, headers=organization1)
    check(f"matricular como ORGANIZATION en curso propio -> {respuesta.status_code} (esperado 201)", respuesta.status_code == 201)

    # --- Una organización no puede matricular en un curso de otra organización ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE2_ID}/students", json={"student_id": STUDENT_A_ID}, headers=organization1)
    check(f"matricular en curso ajeno -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Alumno inexistente ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE1_ID}/students", json={"student_id": 999999}, headers=admin)
    check(f"alumno inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- Curso inexistente ---
    respuesta = requests.post(f"{BASE_URL}/courses/999999/students", json={"student_id": STUDENT_A_ID}, headers=admin)
    check(f"curso inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- Matrícula duplicada ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE1_ID}/students", json={"student_id": STUDENT_A_ID}, headers=admin)
    check(f"matrícula duplicada -> {respuesta.status_code} (esperado 400)", respuesta.status_code == 400)

    # --- Matricular sin enviar ningún token ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE1_ID}/students", json={"student_id": STUDENT_A_ID})
    check(f"matricular sin JWT -> {respuesta.status_code} (esperado 401)", respuesta.status_code == 401)

    # --- Un alumno no puede matricular alumnos ---
    respuesta = requests.post(f"{BASE_URL}/courses/{COURSE1_ID}/students", json={"student_id": STUDENT_A_ID}, headers=student)
    check(f"matricular como STUDENT -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- Eliminar una matrícula existente ---
    respuesta = requests.delete(f"{BASE_URL}/courses/{COURSE1_ID}/students/{STUDENT_B_ID}", headers=admin)
    check(f"eliminar matrícula existente -> {respuesta.status_code} (esperado 200)", respuesta.status_code == 200)

    # --- Eliminar una matrícula que ya no existe (la del paso anterior) ---
    respuesta = requests.delete(f"{BASE_URL}/courses/{COURSE1_ID}/students/{STUDENT_B_ID}", headers=admin)
    check(f"eliminar matrícula inexistente -> {respuesta.status_code} (esperado 404)", respuesta.status_code == 404)

    # --- Una organización no puede eliminar matrículas de un curso de otra organización ---
    respuesta = requests.delete(f"{BASE_URL}/courses/{COURSE2_ID}/students/{STUDENT_A_ID}", headers=organization1)
    check(f"eliminar matrícula de curso ajeno -> {respuesta.status_code} (esperado 403)", respuesta.status_code == 403)

    # --- GET /courses/{course_id}/students ---
    respuesta = requests.get(f"{BASE_URL}/courses/{COURSE1_ID}/students", headers=organization1)
    ids_matriculados = [s["student_id"] for s in respuesta.json()] if respuesta.status_code == 200 else []
    check(
        f"GET /courses/{{id}}/students -> {respuesta.status_code} (esperado 200), matriculados={ids_matriculados}",
        respuesta.status_code == 200 and STUDENT_A_ID in ids_matriculados and STUDENT_B_ID not in ids_matriculados,
    )

    # Limpieza: se desmatricula al alumno que quedó matriculado, para dejar el curso como estaba antes de la prueba
    respuesta = requests.delete(f"{BASE_URL}/courses/{COURSE1_ID}/students/{STUDENT_A_ID}", headers=admin)
    print(f"Limpieza: desmatricular alumno {STUDENT_A_ID} del curso {COURSE1_ID} -> {respuesta.status_code}")


if __name__ == "__main__":
    test_enrollments_api()
