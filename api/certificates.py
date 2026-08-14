from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.authorization import check_certificate_access
from auth.security import ActorType, get_current_actor
from blockchain.blockfrost import verify_stored_certificate_integrity, verify_uploaded_certificate_integrity
from blockchain.transaction import send_transaction
from blockchain.wallet import CARDANO_ADDRESS
from database.connection import get_db
from database.dao import (
    create_certificate,
    get_certificate_by_id,
    get_course_by_id,
    get_organization_by_id,
    get_student_by_id,
    is_student_enrolled,
    list_certificates,
    update_certificate,
)
from database.models import Certificate, CertificateStatus, Course, Organization, Student
from storage.crypto import decrypt_bytes, encrypt_bytes
from storage.pinata import download_from_pinata, upload_bytes_to_pinata
from utils.hash import compute_sha256_bytes

# Router para manejar las rutas relacionadas con certificados
router = APIRouter(
    prefix="/certificates",
    tags=["Certificates"],
)

# Endpoint para subir un certificado. Recibe un archivo PDF, el ID del alumno y el ID del curso.
# Valida el tipo de archivo, calcula el hash SHA-256, cifra el contenido con AES-256-GCM, sube el contenido cifrado a Pinata/IPFS,
# envía la transacción a la red de Cardano y registra el certificado en la base de datos PostgreSQL.
# Requiere JWT y comprueba que el actor autenticado tiene permisos para emitir certificados.
@router.post("/upload")
async def upload_certificate(
    file: UploadFile = File(...),
    student_id: int = Form(...),
    course_id: int = Form(...),
    certificate_name: str = Form(...),
    issuing_organization_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    # Un alumno nunca puede emitir certificados.
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede emitir certificados")

    # La organización emisora se obtiene siempre del actor autenticado, nunca del formulario.
    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        organization_id = current_actor["actor_id"]
    else:
        # Solo un administrador puede indicar la organización emisora en la petición.
        if issuing_organization_id is None:
            raise HTTPException(status_code=400, detail="Debes indicar issuing_organization_id")
        organization = get_organization_by_id(db, issuing_organization_id)
        if organization is None:
            raise HTTPException(status_code=404, detail="Organización no encontrada")
        organization_id = organization.id

    course = get_course_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Impide emitir certificados con cursos que pertenecen a otra organización distinta de la emisora.
    if course.organizacion_id != organization_id:
        raise HTTPException(status_code=403, detail="El curso no pertenece a la organización emisora")

    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # Un certificado solo puede emitirse si existe relación real entre el alumno y el curso (matrícula).
    # Sin esta comprobación, cualquier alumno podría recibir un certificado de un curso al que nunca perteneció.
    if not is_student_enrolled(db, student_id, course_id):
        raise HTTPException(status_code=400, detail="El alumno no está matriculado en este curso")

    # Lee el contenido original y calcula su SHA-256 antes de cifrar. En cardano se almacena el Hash sin cifrar.
    # Esto permite la verificación del PDF original (subido por el alumno/organización).
    content = await file.read()
    sha256_hash = compute_sha256_bytes(content)

    # Cifra el contenido con AES-256-GCM; solo el resultado cifrado se sube a Pinata/IPFS.
    encrypted_content = encrypt_bytes(content)
    cid = upload_bytes_to_pinata(encrypted_content, file.filename, file.content_type)

    # Crea, firma y envía la transacción documental (CID + hash) a la red de Cardano.
    tx_hash = send_transaction(
        destination_address=CARDANO_ADDRESS,
        amount_lovelace=2_000_000,
        cid=cid,
        sha256_hash=sha256_hash,
    )

    # Registra el certificado en PostgreSQL una vez confirmados el CID, el hash y la transacción.
    try:
        certificate = create_certificate(
            db,
            Certificate(
                alumno_id=student_id,
                curso_id=course_id,
                organizacion_emisora_id=organization_id,
                nombre_certificado=certificate_name,
                nombre_archivo=file.filename,
                tipo_contenido=file.content_type,
                tamano_bytes=len(content),
                cid=cid,
                sha256_hash=sha256_hash,
                tx_hash=tx_hash,
                fecha_registro_cardano=datetime.now(timezone.utc),
                estado_registro=CertificateStatus.CONFIRMED,
                revocado=False,
            ),
        )
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al registrar el certificado en la base de datos")

    # Devuelve la información del certificado registrado, incluyendo el ID del certificado, el nombre del archivo, el tipo de contenido,
    # el tamaño en bytes, el hash SHA-256, el CID, el hash de la transacción, si la transacción fue enviada y el estado de registro del certificado.
    return {
        "certificate_id": certificate.id,
        "certificate_name": certificate.nombre_certificado,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "sha256_hash": sha256_hash,
        "cid": cid,
        "tx_hash": tx_hash,
        "transaction_sent": True,
        "registration_status": certificate.estado_registro.value,
    }

# Descarga el PDF original de un certificado. El descifrado es transparente para el
# cliente: nunca se expone el contenido cifrado que realmente está almacenado en IPFS.
# Requiere JWT y comprueba que el actor autenticado tiene acceso a este certificado concreto.
@router.get("/{certificate_id}/download")
async def download_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    certificate = get_certificate_by_id(db, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    check_certificate_access(db, current_actor, certificate)

    encrypted_content = download_from_pinata(certificate.cid)
    original_content = decrypt_bytes(encrypted_content)

    return Response(
        content=original_content,
        media_type=certificate.tipo_contenido,
        headers={"Content-Disposition": f'attachment; filename="{certificate.nombre_archivo}"'},
    )

# Verifica certificado almacenado por la plataforma en IPFS.
# No requiere que el usuario aporte ningún archivo: recupera el tx_hash desde PostgreSQL.
# Compara el hash SHA-256 registrado en Cardano con el hash calculado del contenido recuperado de IPFS.
# Requiere JWT y comprueba que el actor autenticado tiene acceso a este certificado concreto
@router.post("/{certificate_id}/verify-stored-integrity")
async def verify_stored_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    certificate = get_certificate_by_id(db, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    check_certificate_access(db, current_actor, certificate)

    result = verify_stored_certificate_integrity(certificate.tx_hash)

    return {
        "certificate_id": certificate.id,
        "certificate_name": certificate.nombre_certificado,
        "tx_hash": result["tx_hash"],
        "cid": result["cid"],
        "expected_sha256_hash": result["expected_sha256_hash"],
        "calculated_sha256_hash": result["calculated_sha256_hash"],
        "is_valid": result["is_valid"],
        "result": "CERTIFICADO INTEGRO (INTEGRIDAD VERIFICADA)" if result["is_valid"] else "VERIFICACIÓN DE INTEGRIDAD FALLIDA"
    }

# Verifica una copia del certificado aportada por el usuario (alumno/organización) .
# Compara el PDF recibido contra el hash registrado en Cardano, sin consultar IPFS.
# Requiere JWT y comprueba que el actor autenticado tiene acceso a este certificado concreto.
@router.post("/{certificate_id}/verify-uploaded-integrity")
async def verify_uploaded_certificate(
    certificate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    certificate = get_certificate_by_id(db, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    check_certificate_access(db, current_actor, certificate)

    uploaded_content = await file.read()
    result = verify_uploaded_certificate_integrity(certificate.tx_hash, uploaded_content)

    return {
        "certificate_id": certificate.id,
        "certificate_name": certificate.nombre_certificado,
        "filename": file.filename,
        "tx_hash": result["tx_hash"],
        "expected_sha256_hash": result["expected_sha256_hash"],
        "uploaded_sha256_hash": result["uploaded_sha256_hash"],
        "is_valid": result["is_valid"],
        "result": "CERTIFICADO INTEGRO (INTEGRIDAD VERIFICADA)" if result["is_valid"] else "VERIFICACIÓN DE INTEGRIDAD FALLIDA",
    }

# Cuerpo de la petición de revocación: el motivo es obligatorio (se valida en el propio endpoint,
# porque una cadena vacía o solo espacios es un "reason" válido para Pydantic pero no para nosotros).
class RevokeCertificateRequest(BaseModel):
    reason: str | None = None


# Revoca un certificado: marca revocado=True y guarda el motivo (obligatorio) y la fecha de la revocación.
# El certificado sigue existiendo, siendo consultable, descargable y verificable; solo deja de considerarse vigente.
# Puede revocar un administrador (cualquier certificado) o la organización que lo emitió.
@router.post("/{certificate_id}/revoke")
async def revoke_certificate(
    certificate_id: int,
    request: RevokeCertificateRequest | None = None,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    certificate = get_certificate_by_id(db, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede revocar certificados")

    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        if certificate.organizacion_emisora_id != current_actor["actor_id"]:
            raise HTTPException(status_code=403, detail="Solo la organización emisora puede revocar este certificado")

    if certificate.revocado:
        raise HTTPException(status_code=400, detail="El certificado ya está revocado")

    if request is None or not request.reason or not request.reason.strip():
        raise HTTPException(status_code=400, detail="Debes indicar el motivo de la revocación")

    certificate.revocado = True
    certificate.motivo_revocacion = request.reason.strip()
    certificate.fecha_revocacion = datetime.now(timezone.utc)
    certificate = update_certificate(db, certificate)

    return {
        "certificate_id": certificate.id,
        "revoked": certificate.revocado,
        "revocation_reason": certificate.motivo_revocacion,
        "revoked_at": certificate.fecha_revocacion,
    }

# Construye el resumen de un certificado con los datos de alumno, curso y organización ya cargados.
# Se reutiliza en los tres endpoints de listado para garantizar que devuelven siempre el mismo formato.
def build_certificate_summary(certificate: Certificate, student: Student, course: Course, organization: Organization) -> dict:
    return {
        "certificate_id": certificate.id,
        "certificate_name": certificate.nombre_certificado,
        "student_name": f"{student.nombre} {student.apellidos}",
        "course_title": course.titulo,
        "organization_name": organization.nombre,
        "course_teacher": course.docente,
        "course_hours": course.horas,
        "created_at": certificate.fecha_creacion,
        "registration_status": certificate.estado_registro.value,
        "revoked": certificate.revocado,
    }


# Endpoint para listar todos los certificados con un resumen preparado para el frontend.
# Consulta únicamente PostgreSQL a través del DAO, sin volver a consultar Cardano ni IPFS.
# Restringe el listado global de certificados a los administradores.
@router.get("")
async def get_certificates(db: Session = Depends(get_db), current_actor: dict = Depends(get_current_actor)):
    if current_actor["actor_type"] != ActorType.ADMINISTRATOR.value:
        raise HTTPException(status_code=403, detail="Solo un administrador puede consultar el listado completo de certificados")

    certificates = list_certificates(db)

    summaries = []
    for certificate in certificates:
        student = get_student_by_id(db, certificate.alumno_id)
        if student is None:
            raise HTTPException(status_code=500, detail=f"Alumno asociado no encontrado (alumno_id={certificate.alumno_id})")

        course = get_course_by_id(db, certificate.curso_id)
        if course is None:
            raise HTTPException(status_code=500, detail=f"Curso asociado no encontrado (curso_id={certificate.curso_id})")

        organization = get_organization_by_id(db, certificate.organizacion_emisora_id)
        if organization is None:
            raise HTTPException(
                status_code=500,
                detail=f"Organización emisora no encontrada (organizacion_id={certificate.organizacion_emisora_id})",
            )

        summaries.append(build_certificate_summary(certificate, student, course, organization))

    return summaries

# Endpoint para consultar un certificado ya registrado, junto con los datos del alumno, el curso y la organización emisora.
# Requiere JWT y comprueba que el actor autenticado tiene acceso a este certificado concreto.
@router.get("/{certificate_id}")
async def get_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    certificate = get_certificate_by_id(db, certificate_id)

    if certificate is None:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    check_certificate_access(db, current_actor, certificate)

    student = get_student_by_id(db, certificate.alumno_id)
    if student is None:
        raise HTTPException(status_code=500, detail=f"Alumno asociado no encontrado (alumno_id={certificate.alumno_id})")

    course = get_course_by_id(db, certificate.curso_id)
    if course is None:
        raise HTTPException(status_code=500, detail=f"Curso asociado no encontrado (curso_id={certificate.curso_id})")

    organization = get_organization_by_id(db, certificate.organizacion_emisora_id)
    if organization is None:
        raise HTTPException(
            status_code=500,
            detail=f"Organización emisora no encontrada (organizacion_id={certificate.organizacion_emisora_id})",
        )

    return {
        "certificate_id": certificate.id,
        "certificate_name": certificate.nombre_certificado,
        "student": {
            "id": student.id,
            "name": student.nombre,
            "last_names": student.apellidos,
        },
        "course": {
            "id": course.id,
            "title": course.titulo,
            "teacher": course.docente,
            "hours": course.horas,
        },
        "organization": {
            "id": organization.id,
            "name": organization.nombre,
        },
        "content_type": certificate.tipo_contenido,
        "size_bytes": certificate.tamano_bytes,
        "cid": certificate.cid,
        "sha256_hash": certificate.sha256_hash,
        "tx_hash": certificate.tx_hash,
        "registration_status": certificate.estado_registro.value,
        "revoked": certificate.revocado,
        "revocation_reason": certificate.motivo_revocacion,
        "revoked_at": certificate.fecha_revocacion,
        "created_at": certificate.fecha_creacion,
        "cardano_registration_date": certificate.fecha_registro_cardano,
    }

