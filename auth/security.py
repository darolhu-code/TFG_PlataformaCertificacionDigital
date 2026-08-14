# Contiene funciones de seguridad para la API, incluyendo la creación y verificación de JWT, así como el hashing de contraseñas.
import os
from datetime import datetime, timedelta, timezone
from enum import Enum

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.connection import get_db
from database.dao import get_administrator_by_id, get_organization_by_id, get_student_by_id

load_dotenv()
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"])

# auto_error=False para poder devolver siempre 401 (en vez del 403 por defecto) cuando falta el token.
bearer_scheme = HTTPBearer(auto_error=False)


# Tipo de actor autenticado.
class ActorType(str, Enum):
    STUDENT = "STUDENT"
    ORGANIZATION = "ORGANIZATION"
    ADMINISTRATOR = "ADMINISTRATOR"


# genera el hash seguro de una contraseña con bcrypt
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# comprueba si una contraseña en texto plano coincide con su hash almacenado
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# crea un JWT firmado con la identidad mínima del actor (id + tipo) y su fecha de expiración
def create_access_token(actor_id: int, actor_type: ActorType) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"actor_id": actor_id, "actor_type": actor_type.value, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# decodifica un JWT verificando su firma y expiración; lanza una excepción si no es válido
def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


# Dependencia de FastAPI: valida el JWT y comprueba que el actor sigue existiendo en PostgreSQL.
# Es la función que se utiliza en los endpoints de la API para obtener el actor autenticado a partir del token (autenticación)
def get_current_actor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no válidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise unauthorized

    actor_id = payload.get("actor_id")
    actor_type = payload.get("actor_type")

    if actor_type == ActorType.STUDENT.value:
        actor = get_student_by_id(db, actor_id)
    elif actor_type == ActorType.ORGANIZATION.value:
        actor = get_organization_by_id(db, actor_id)
    elif actor_type == ActorType.ADMINISTRATOR.value:
        actor = get_administrator_by_id(db, actor_id)
    else:
        raise unauthorized

    # Rechaza el token si la cuenta se ha eliminado después de haberlo emitido.
    if actor is None:
        raise unauthorized

    return {"actor": actor, "actor_id": actor_id, "actor_type": actor_type}
