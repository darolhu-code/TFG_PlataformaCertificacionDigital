# Contiene funciones de autorización para la API, incluyendo la verificación de permisos de acceso a certificados.
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from auth.security import ActorType
from database.dao import has_permission
from database.models import Certificate


# Comprueba que el actor autenticado tiene acceso al certificado solicitado; lanza 403 si no.
# Es la función que se utiliza en los endpoints de la API para proteger el acceso a certificados (autorización)
def check_certificate_access(db: Session, current_actor: dict, certificate: Certificate) -> bool:
    actor_id = current_actor["actor_id"]
    actor_type = current_actor["actor_type"]
    forbidden = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a este certificado")

    # Un administrador puede acceder a cualquier certificado de la plataforma.
    if actor_type == ActorType.ADMINISTRATOR.value:
        return True

    # Un alumno solo puede acceder a sus propios certificados.
    if actor_type == ActorType.STUDENT.value:
        if certificate.alumno_id == actor_id:
            return True
        raise forbidden

    # Una organización puede acceder si es la emisora o dispone de permiso del alumno.
    if actor_type == ActorType.ORGANIZATION.value:
        if certificate.organizacion_emisora_id == actor_id:
            return True
        if has_permission(db, certificate.alumno_id, actor_id):
            return True
        raise forbidden

    raise forbidden
