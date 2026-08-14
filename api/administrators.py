# Contiene los endpoints de gestión de administradores (crear, listar, consultar).
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import ActorType, get_current_actor, hash_password
from database.connection import get_db
from database.dao import (
    create_administrator,
    get_administrator_by_dni,
    get_administrator_by_email,
    get_administrator_by_id,
    list_administrators,
)
from database.models import Administrator

# Router para manejar las rutas relacionadas con administradores
router = APIRouter(
    prefix="/administrators",
    tags=["Administrators"],
)


# Cuerpo de la petición para crear un administrador.
class CreateAdministratorRequest(BaseModel):
    dni: str
    nombre: str
    apellidos: str
    email: str
    password: str


# Construye la respuesta de un administrador, sin exponer nunca password_hash.
def build_administrator_summary(administrator: Administrator) -> dict:
    return {
        "administrator_id": administrator.id,
        "dni": administrator.dni,
        "nombre": administrator.nombre,
        "apellidos": administrator.apellidos,
        "email": administrator.email,
        "activo": administrator.activo,
        "fecha_creacion": administrator.fecha_creacion,
    }


# Endpoint para crear un administrador. Solo puede hacerlo otro administrador; ni una organización ni un
# alumno pueden crear administradores. Valida que el DNI y el email no estén ya en uso, y guarda la
# contraseña con el mismo mecanismo de hash (bcrypt) que utiliza el resto del sistema.
@router.post("", status_code=201)
async def create_administrator_endpoint(
    request: CreateAdministratorRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] != ActorType.ADMINISTRATOR.value:
        raise HTTPException(status_code=403, detail="Solo un administrador puede crear administradores")

    if get_administrator_by_dni(db, request.dni) is not None:
        raise HTTPException(status_code=400, detail="Ya existe un administrador con ese DNI")

    if get_administrator_by_email(db, request.email) is not None:
        raise HTTPException(status_code=400, detail="Ya existe un administrador con ese email")

    administrator = create_administrator(
        db,
        Administrator(
            dni=request.dni,
            nombre=request.nombre,
            apellidos=request.apellidos,
            email=request.email,
            password_hash=hash_password(request.password),
            activo=True,
        ),
    )

    return build_administrator_summary(administrator)


# Endpoint para listar todos los administradores de la plataforma. Solo accesible para un administrador.
@router.get("")
async def get_administrators(db: Session = Depends(get_db), current_actor: dict = Depends(get_current_actor)):
    if current_actor["actor_type"] != ActorType.ADMINISTRATOR.value:
        raise HTTPException(status_code=403, detail="Solo un administrador puede consultar el listado de administradores")

    administrators = list_administrators(db)

    return [build_administrator_summary(administrator) for administrator in administrators]


# Endpoint para consultar el detalle de un administrador. Solo accesible para un administrador.
@router.get("/{administrator_id}")
async def get_administrator(
    administrator_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] != ActorType.ADMINISTRATOR.value:
        raise HTTPException(status_code=403, detail="Solo un administrador puede consultar el detalle de un administrador")

    administrator = get_administrator_by_id(db, administrator_id)
    if administrator is None:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")

    return build_administrator_summary(administrator)
