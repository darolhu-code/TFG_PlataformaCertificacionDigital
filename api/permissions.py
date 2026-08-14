from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import ActorType, get_current_actor
from database.connection import get_db
from database.dao import (
    get_organization_by_id,
    get_student_by_id,
    grant_permission,
    list_all_active_permissions,
    list_organization_permissions,
    list_user_permissions,
    revoke_permission,
)

# Router para manejar las rutas relacionadas con los permisos de acceso a certificados
router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
)

# Cuerpo de la petición conceder permiso/autorizar
class PermissionRequest(BaseModel):
    organization_id: int


# Concede permiso a una organización para ver todos los certificados del alumno autenticado.
# El alumno autenticado solo puede gestionar sus propios permisos: se obtiene del JWT, nunca del cliente.
@router.post("/grant")
async def grant_access_permission(
    request: PermissionRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] != ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Solo un alumno puede conceder permisos sobre sus certificados")

    organization = get_organization_by_id(db, request.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    student_id = current_actor["actor_id"]
    permission = grant_permission(db, student_id, request.organization_id)

    return {
        "organization_id": organization.id,
        "organization_name": organization.nombre,
        "active": permission.activo,
    }


# Revoca el permiso de una organización sobre los certificados del alumno autenticado, sin borrar la fila (activo=False).
@router.post("/revoke")
async def revoke_access_permission(
    request: PermissionRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] != ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Solo un alumno puede revocar permisos sobre sus certificados")

    organization = get_organization_by_id(db, request.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    student_id = current_actor["actor_id"]
    revoke_permission(db, student_id, request.organization_id)

    return {
        "organization_id": organization.id,
        "organization_name": organization.nombre,
        "active": False,
    }


# Consulta de permisos, distinta según el actor autenticado:
# - un alumno ve las organizaciones a las que ha concedido permiso activo.
# - una organización ve qué alumnos le han concedido permiso a ella.
# - un administrador ve todos los permisos activos de la plataforma.
# En los tres casos es de solo lectura: conceder/revocar sigue siendo exclusivo del alumno vía /grant y /revoke.
@router.get("")
async def get_permissions(db: Session = Depends(get_db), current_actor: dict = Depends(get_current_actor)):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        student_id = current_actor["actor_id"]
        organizations = list_user_permissions(db, student_id)

        return [
            {"organization_id": organization.id, "organization_name": organization.nombre, "active": True}
            for organization in organizations
        ]

    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        permissions = list_organization_permissions(db, current_actor["actor_id"])

        results = []
        for permission in permissions:
            student = get_student_by_id(db, permission.alumno_id)
            if student is None:
                raise HTTPException(status_code=500, detail=f"Alumno asociado no encontrado (alumno_id={permission.alumno_id})")

            results.append({
                "student_id": student.id,
                "student_name": f"{student.nombre} {student.apellidos}",
                "granted_at": permission.fecha_creacion,
            })
        return results

    # ActorType.ADMINISTRATOR
    permissions = list_all_active_permissions(db)

    results = []
    for permission in permissions:
        student = get_student_by_id(db, permission.alumno_id)
        if student is None:
            raise HTTPException(status_code=500, detail=f"Alumno asociado no encontrado (alumno_id={permission.alumno_id})")

        organization = get_organization_by_id(db, permission.organizacion_id)
        if organization is None:
            raise HTTPException(status_code=500, detail=f"Organización asociada no encontrada (organizacion_id={permission.organizacion_id})")

        results.append({
            "student_id": student.id,
            "student_name": f"{student.nombre} {student.apellidos}",
            "organization_id": organization.id,
            "organization_name": organization.nombre,
            "granted_at": permission.fecha_creacion,
        })
    return results
