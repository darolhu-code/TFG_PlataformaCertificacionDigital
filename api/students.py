# Contiene los endpoints de gestión de alumnos (crear, listar, consultar) y el listado de sus certificados.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.certificates import build_certificate_summary
from auth.security import ActorType, get_current_actor, hash_password
from database.connection import get_db
from database.dao import (
    create_student,
    get_course_by_id,
    get_organization_by_id,
    get_student_by_dni,
    get_student_by_email,
    get_student_by_id,
    list_student_certificates,
    list_students,
)
from database.models import Student

# Router para manejar las rutas relacionadas con alumnos
router = APIRouter(
    prefix="/students",
    tags=["Students"],
)


# Cuerpo de la petición para crear un alumno.
class CreateStudentRequest(BaseModel):
    dni: str
    nombre: str
    apellidos: str
    email: str
    password: str


# Construye la respuesta de un alumno, sin exponer nunca password_hash.
def build_student_summary(student: Student) -> dict:
    return {
        "student_id": student.id,
        "dni": student.dni,
        "nombre": student.nombre,
        "apellidos": student.apellidos,
        "email": student.email,
        "activo": student.activo,
        "fecha_creacion": student.fecha_creacion,
    }


# Endpoint para crear un alumno. Solo puede hacerlo un administrador o una organización; un alumno no
# puede crear otros alumnos. Valida que el DNI y el email no estén ya en uso, y guarda la contraseña
# con el mismo mecanismo de hash (bcrypt) que utiliza el resto del sistema.
@router.post("", status_code=201)
async def create_student_endpoint(
    request: CreateStudentRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede crear otros alumnos")

    if get_student_by_dni(db, request.dni) is not None:
        raise HTTPException(status_code=400, detail="Ya existe un alumno con ese DNI")

    if get_student_by_email(db, request.email) is not None:
        raise HTTPException(status_code=400, detail="Ya existe un alumno con ese email")

    student = create_student(
        db,
        Student(
            dni=request.dni,
            nombre=request.nombre,
            apellidos=request.apellidos,
            email=request.email,
            password_hash=hash_password(request.password),
            activo=True,
        ),
    )

    return build_student_summary(student)


# Endpoint para listar todos los alumnos de la plataforma. Accesible para administradores y
# organizaciones; un alumno no puede consultar el listado completo.
@router.get("")
async def get_students(db: Session = Depends(get_db), current_actor: dict = Depends(get_current_actor)):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede consultar el listado de alumnos")

    students = list_students(db)

    return [build_student_summary(student) for student in students]


# Endpoint para consultar el detalle de un alumno. Accesible para administradores y organizaciones;
# un alumno no puede consultar el detalle de otro alumno por esta vía.
@router.get("/{student_id}")
async def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede consultar el detalle de otro alumno")

    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    return build_student_summary(student)


# Endpoint para listar los certificados de un alumno, con el mismo formato resumido que GET /certificates.
# Requiere JWT y comprueba que el actor autenticado tiene acceso a los certificados del alumno solicitado.
# Consulta únicamente PostgreSQL a través del DAO, sin volver a consultar Cardano ni IPFS.
@router.get("/{student_id}/certificates")
async def get_student_certificates(
    student_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # Un alumno solo puede consultar su propio listado; una organización no debe usar este endpoint.
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        if current_actor["actor_id"] != student_id:
            raise HTTPException(status_code=403, detail="No puedes consultar los certificados de otro alumno")
    elif current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        raise HTTPException(status_code=403, detail="Las organizaciones deben usar /organizations/{organization_id}/certificates")

    # Consulta los certificados del alumno y construye un resumen de cada uno, incluyendo el nombre del certificado, el curso y la organización emisora.
    certificates = list_student_certificates(db, student_id)
    summaries = []
    for certificate in certificates:
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
