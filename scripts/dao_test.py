# Script de prueba para probar el flujo completo del DAO: crea organización, alumno, curso y certificado, y valida las consultas
import uuid
from datetime import datetime, timezone

from auth.security import hash_password
from database.connection import SessionLocal
from database.dao import (
    create_certificate,
    create_course,
    create_organization,
    create_student,
    get_certificate_by_id,
    list_organization_certificates,
    list_student_certificates,
)
from database.models import Certificate, CertificateStatus, Course, Organization, Student


# prueba el flujo completo del DAO: crea organización, alumno, curso y certificado, y valida las consultas
def test_dao():
    db = SessionLocal()

    try:
        unique_id = uuid.uuid4().hex

        print("=" * 30)
        print("Prueba DAO PostgreSQL")
        print("=" * 30)
        print()

        # crea una organización de prueba
        organization = create_organization(
            db,
            Organization(
                nombre="Organización de prueba",
                tipo="Administración pública",
                email=f"organizacion_{unique_id}@test.com",
                password_hash=hash_password("password"),
            ),
        )
        print("Organización creada:")
        print(f"ID: {organization.id}")
        print()

        # crea un alumno de prueba
        student = create_student(
            db,
            Student(
                dni=f"TEST{unique_id[:12]}",
                nombre="Alumno",
                apellidos="De prueba",
                email=f"alumno_{unique_id}@test.com",
                password_hash=hash_password("password"),
            ),
        )
        print("Alumno creado:")
        print(f"ID: {student.id}")
        print()

        # crea un curso asociado a la organización de prueba
        course = create_course(
            db,
            Course(
                organizacion_id=organization.id,
                titulo="Curso de prueba",
                descripcion="Curso creado para probar el acceso a PostgreSQL",
                docente="Docente de prueba",
                horas=20,
            ),
        )
        print("Curso creado:")
        print(f"ID: {course.id}")
        print()

        # crea un certificado asociado al alumno, al curso y a la organización emisora
        certificate = create_certificate(
            db,
            Certificate(
                alumno_id=student.id,
                curso_id=course.id,
                organizacion_emisora_id=organization.id,
                nombre_certificado="Certificado de prueba",
                nombre_archivo="certificado_prueba.pdf",
                tipo_contenido="application/pdf",
                tamano_bytes=10235,
                cid=f"cid_test_{unique_id}",
                sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                tx_hash=uuid.uuid4().hex + uuid.uuid4().hex,
                estado_registro=CertificateStatus.CONFIRMED,
                fecha_registro_cardano=datetime.now(timezone.utc),
                revocado=False,
            ),
        )
        print("Certificado creado:")
        print(f"ID: {certificate.id}")
        print()

        # recupera el certificado recién creado mediante el DAO
        fetched_certificate = get_certificate_by_id(db, certificate.id)
        print("Certificado recuperado:")
        print(f"Archivo: {fetched_certificate.nombre_archivo}")
        print(f"CID: {fetched_certificate.cid}")
        print(f"Tx hash: {fetched_certificate.tx_hash}")
        print()

        # lista los certificados del alumno y los emitidos por la organización
        student_certificates = list_student_certificates(db, student.id)
        organization_certificates = list_organization_certificates(db, organization.id)

        print(f"Certificados del alumno: {len(student_certificates)}")
        print(f"Certificados emitidos por la organización: {len(organization_certificates)}")
        print()
        print("Prueba DAO: OK")

    except Exception as e:
        db.rollback()
        print("Prueba DAO: KO")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    test_dao()
