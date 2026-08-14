# Prueba end-to-end de la API de permisos, reutilizando alumno/organizaciones ya existentes en la base de datos.
# Requiere el servidor arrancado (uvicorn main:app --reload).
import requests

from auth.security import ActorType, create_access_token
from database.connection import SessionLocal
from database.models import AccessPermission

BASE_URL = "http://127.0.0.1:8000"

# Alumno 1 tiene certificados propios y, de partida, no ha dado permiso a la organización 4.
STUDENT_ID = 1
ORG_ID = 4


def check(label, condition):
    print(f"{'OK   ' if condition else 'FALLO'} {label}")


def permiso_activo(db):
    row = db.query(AccessPermission).filter_by(alumno_id=STUDENT_ID, organizacion_id=ORG_ID).first()
    return row.activo if row else None


def test_permissions_api():
    student = {"Authorization": f"Bearer {create_access_token(STUDENT_ID, ActorType.STUDENT)}"}
    organization = {"Authorization": f"Bearer {create_access_token(ORG_ID, ActorType.ORGANIZATION)}"}
    admin = {"Authorization": f"Bearer {create_access_token(1, ActorType.ADMINISTRATOR)}"}

    try:
        requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print(f"No se puede conectar con {BASE_URL}. Arranca antes el servidor: uvicorn main:app --reload")
        return

    # Seguridad básica: solo un alumno puede gestionar sus permisos
    r = requests.post(f"{BASE_URL}/permissions/grant", json={"organization_id": ORG_ID})
    check(f"grant sin JWT -> {r.status_code} (401)", r.status_code == 401)

    r = requests.post(f"{BASE_URL}/permissions/grant", json={"organization_id": ORG_ID}, headers=organization)
    check(f"grant como ORGANIZATION -> {r.status_code} (403)", r.status_code == 403)

    r = requests.post(f"{BASE_URL}/permissions/grant", json={"organization_id": ORG_ID}, headers=admin)
    check(f"grant como ADMINISTRATOR -> {r.status_code} (403)", r.status_code == 403)

    r = requests.post(f"{BASE_URL}/permissions/grant", json={"organization_id": 999999}, headers=student)
    check(f"grant a organización inexistente -> {r.status_code} (404)", r.status_code == 404)

    # Conceder permiso
    r = requests.post(f"{BASE_URL}/permissions/grant", json={"organization_id": ORG_ID}, headers=student)
    check(f"grant -> {r.status_code} (200), active={r.json().get('active')}", r.status_code == 200 and r.json().get("active") is True)

    db = SessionLocal()
    check(f"BBDD tras grant: activo={permiso_activo(db)}", permiso_activo(db) is True)
    db.close()

    r = requests.get(f"{BASE_URL}/permissions", headers=student)
    org_ids = [p["organization_id"] for p in r.json()]
    check(f"listado del alumno incluye la organización: {org_ids}", ORG_ID in org_ids)

    r = requests.get(f"{BASE_URL}/organizations/{ORG_ID}/certificates", headers=organization)
    check(f"organización ve certificados del alumno tras conceder: {len(r.json())}", len(r.json()) > 0)

    # Revocar permiso
    r = requests.post(f"{BASE_URL}/permissions/revoke", json={"organization_id": ORG_ID}, headers=student)
    check(f"revoke -> {r.status_code} (200)", r.status_code == 200)

    db = SessionLocal()
    check(f"BBDD tras revoke: activo={permiso_activo(db)}", permiso_activo(db) is False)
    db.close()

    r = requests.get(f"{BASE_URL}/organizations/{ORG_ID}/certificates", headers=organization)
    check(f"organización deja de ver certificados tras revocar: {len(r.json())}", len(r.json()) == 0)

    # Reactivación: no debe duplicar la fila
    requests.post(f"{BASE_URL}/permissions/grant", json={"organization_id": ORG_ID}, headers=student)
    db = SessionLocal()
    rows = db.query(AccessPermission).filter_by(alumno_id=STUDENT_ID, organizacion_id=ORG_ID).all()
    check(f"reactivación sin duplicar fila: {len(rows)} fila(s), activo={rows[0].activo}", len(rows) == 1 and rows[0].activo is True)
    db.close()

    # Deja el estado como estaba antes de la prueba
    requests.post(f"{BASE_URL}/permissions/revoke", json={"organization_id": ORG_ID}, headers=student)


if __name__ == "__main__":
    test_permissions_api()
