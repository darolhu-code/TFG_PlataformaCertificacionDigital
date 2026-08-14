# Contiene la lógica de autenticación y autorización de la API, incluyendo el manejo de JWT y la verificación de permisos de acceso a certificados.

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import ActorType, create_access_token, get_current_actor, verify_password
from database.connection import get_db
from database.dao import get_administrator_by_email, get_organization_by_email, get_student_by_email

# Router para manejar las rutas de autenticación
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

# Cuerpo de la petición para logearse en la aplicación
class LoginRequest(BaseModel):
    email: str
    password: str


# Busca el email entre alumnos, organizaciones y administradores, en ese orden, hasta encontrar una cuenta.
def find_actor_by_email(db: Session, email: str):
    student = get_student_by_email(db, email)
    if student is not None:
        return student, ActorType.STUDENT

    organization = get_organization_by_email(db, email)
    if organization is not None:
        return organization, ActorType.ORGANIZATION

    administrator = get_administrator_by_email(db, email)
    if administrator is not None:
        return administrator, ActorType.ADMINISTRATOR

    return None, None


# Login único para alumnos, organizaciones y administradores
@router.post("/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    invalid_credentials = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos")

    actor, actor_type = find_actor_by_email(db, credentials.email)
    if actor is None:
        raise invalid_credentials

    if not verify_password(credentials.password, actor.password_hash):
        raise invalid_credentials

    access_token = create_access_token(actor.id, actor_type)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "actor_type": actor_type.value,
    }


# Endpoint para validar el correcto funcionamiento delflujo JWT.
# Permite al cliente comprobar que el token sigue siendo válido y obtener la identidad del actor autenticado.
@router.get("/me")
async def get_me(current=Depends(get_current_actor)):
    actor = current["actor"]

    # Las organizaciones solo tienen nombre; alumnos y administradores tienen nombre y apellidos.
    if current["actor_type"] == ActorType.ORGANIZATION.value:
        display_name = actor.nombre
    else:
        display_name = f"{actor.nombre} {actor.apellidos}"

    return {
        "actor_id": current["actor_id"],
        "actor_type": current["actor_type"],
        "display_name": display_name,
        "email": actor.email,
    }
