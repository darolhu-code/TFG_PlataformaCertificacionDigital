# Script de prueba para el flujo de permisos de acceso: concede, comprueba, lista y revoca un permiso
from database.connection import SessionLocal
from database.dao import grant_permission, has_permission, list_user_permissions, revoke_permission
from database.models import Organization, Student


# prueba el flujo completo de permisos reutilizando el primer alumno y la primera organización existentes
def test_permissions():
    db = SessionLocal()

    try:
        student = db.query(Student).first()
        organization = db.query(Organization).first()

        if student is None or organization is None:
            print("No hay alumnos u organizaciones en la base de datos. Ejecuta antes scripts.dao_test")
            return

        print("=" * 30)
        print("Prueba de permisos de acceso")
        print("=" * 30)
        print()
        print(f"Alumno: {student.nombre} {student.apellidos} (id={student.id})")
        print(f"Organización: {organization.nombre} (id={organization.id})")
        print()

        # concede permiso a la organización sobre los certificados del alumno
        permission = grant_permission(db, student.id, organization.id)
        print(f"Permiso concedido: activo={permission.activo}")

        # comprueba que el permiso está activo
        print(f"¿Tiene permiso? {has_permission(db, student.id, organization.id)}")
        print()

        # lista las organizaciones con permiso activo sobre el alumno
        permitted_organizations = list_user_permissions(db, student.id)
        print(f"Organizaciones con permiso sobre el alumno: {[org.nombre for org in permitted_organizations]}")
        print()

        # revoca el permiso concedido
        permission = revoke_permission(db, student.id, organization.id)
        print(f"Permiso revocado: activo={permission.activo}")
        print(f"¿Tiene permiso tras revocar? {has_permission(db, student.id, organization.id)}")
        print()
        print("Prueba de permisos: OK")

    except Exception as e:
        db.rollback()
        print("Prueba de permisos: KO")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    test_permissions()
