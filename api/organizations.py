# Contiene los endpoints de gestión de organizaciones (crear, listar, consultar) y el listado de sus certificados.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.certificates import build_certificate_summary
from auth.security import ActorType, get_current_actor, hash_password
from database.connection import get_db
from database.dao import (
    create_organization,
    get_course_by_id,
    get_organization_by_email,
    get_organization_by_id,
    get_student_by_id,
    list_organization_certificates,
    list_organizations,
    list_permitted_certificates,
)
from database.models import Organization

# Router para manejar las rutas relacionadas con organizaciones
router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


# Cuerpo de la petición para crear una organización.
class CreateOrganizationRequest(BaseModel):
    nombre: str
    tipo: str
    email: str
    password: str


# Construye la respuesta de una organización, sin exponer nunca password_hash.
def build_organization_summary(organization: Organization) -> dict:
    return {
        "organization_id": organization.id,
        "nombre": organization.nombre,
        "tipo": organization.tipo,
        "email": organization.email,
        "activo": organization.activo,
        "fecha_creacion": organization.fecha_creacion,
    }


# Endpoint para crear una organización. Solo puede hacerlo un administrador; ni una organización ni un
# alumno pueden crear otras organizaciones. Valida que el email no esté ya en uso, y guarda la contraseña
# con el mismo mecanismo de hash (bcrypt) que utiliza el resto del sistema.
@router.post("", status_code=201)
async def create_organization_endpoint(
    request: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] != ActorType.ADMINISTRATOR.value:
        raise HTTPException(status_code=403, detail="Solo un administrador puede crear organizaciones")

    if get_organization_by_email(db, request.email) is not None:
        raise HTTPException(status_code=400, detail="Ya existe una organización con ese email")

    organization = create_organization(
        db,
        Organization(
            nombre=request.nombre,
            tipo=request.tipo,
            email=request.email,
            password_hash=hash_password(request.password),
            activo=True,
        ),
    )

    return build_organization_summary(organization)


# Endpoint para listar todas las organizaciones de la plataforma (sin filtrar). Pensado para que un alumno
# pueda ver todas las organizaciones a la hora de conceder/revocar permisos de acceso a sus certificados;
# no requiere ser de un tipo de actor concreto, cualquiera autenticado puede consultarlo.
@router.get("")
async def get_organizations(db: Session = Depends(get_db), current_actor: dict = Depends(get_current_actor)):
    organizations = list_organizations(db)
    return [
        {"organization_id": organization.id, "organization_name": organization.nombre, "organization_type": organization.tipo}
        for organization in organizations
    ]


# Endpoint para consultar el detalle de una organización. Solo accesible para un administrador.
@router.get("/{organization_id}")
async def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] != ActorType.ADMINISTRATOR.value:
        raise HTTPException(status_code=403, detail="Solo un administrador puede consultar el detalle de una organización")

    organization = get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    return build_organization_summary(organization)


# Endpoint para listar los certificados visibles para una organización: los que ella misma ha emitido y los
# que tiene autorizados por permiso de algún alumno (ver access_type en cada certificado devuelto). Mismo
# formato resumido que GET /certificates. Consulta únicamente PostgreSQL a través del DAO, sin volver a
# consultar Cardano ni IPFS.
@router.get("/{organization_id}/certificates")
async def get_organization_certificates(
    organization_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    organization = get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    # Un alumno nunca puede usar este endpoint; una organización solo puede consultar su propio listado.
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Los alumnos deben usar /students/{student_id}/certificates")
    elif current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        if current_actor["actor_id"] != organization_id:
            raise HTTPException(status_code=403, detail="No puedes consultar los certificados de otra organización")

    # Une los certificados emitidos por la organización con los autorizados por permiso, sin duplicados
    # (un certificado puede estar en ambos listados a la vez si además fue autorizado por permiso).
    issued_certificates = list_organization_certificates(db, organization_id)
    permitted_certificates = list_permitted_certificates(db, organization_id)

    seen_certificate_ids = []
    certificates = []
    for certificate in issued_certificates + permitted_certificates:
        if certificate.id not in seen_certificate_ids:
            seen_certificate_ids.append(certificate.id)
            certificates.append(certificate)

    summaries = []
    for certificate in certificates:
        student = get_student_by_id(db, certificate.alumno_id)
        if student is None:
            raise HTTPException(status_code=500, detail=f"Alumno asociado no encontrado (alumno_id={certificate.alumno_id})")

        course = get_course_by_id(db, certificate.curso_id)
        if course is None:
            raise HTTPException(status_code=500, detail=f"Curso asociado no encontrado (curso_id={certificate.curso_id})")

        # La organización emisora real del certificado no tiene por qué ser la organización que consulta
        # (puede estar viéndolo por permiso), así que se obtiene por certificado, igual que en los otros endpoints.
        issuing_organization = get_organization_by_id(db, certificate.organizacion_emisora_id)
        if issuing_organization is None:
            raise HTTPException(
                status_code=500,
                detail=f"Organización emisora no encontrada (organizacion_id={certificate.organizacion_emisora_id})",
            )

        summary = build_certificate_summary(certificate, student, course, issuing_organization)
        # Indica si el certificado aparece en el listado porque la organización lo emitió ella misma
        # o porque tiene acceso por un permiso concedido por el alumno (solo relevante para organizaciones).
        summary["access_type"] = "ISSUED" if certificate.organizacion_emisora_id == organization_id else "PERMISSION"
        summaries.append(summary)

    return summaries
