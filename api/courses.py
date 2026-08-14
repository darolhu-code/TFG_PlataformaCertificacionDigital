# Contiene los endpoints de consulta y gestión de cursos
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.security import ActorType, get_current_actor
from database.connection import get_db
from database.dao import (
    create_course,
    create_enrollment,
    delete_enrollment,
    get_course_by_id,
    get_enrollment,
    get_organization_by_id,
    get_student_by_id,
    is_student_enrolled,
    list_course_students,
    list_courses,
    list_organization_courses,
)
from database.models import Course, CourseEnrollment, Organization

# Router para manejar las rutas relacionadas con cursos
router = APIRouter(
    prefix="/courses",
    tags=["Courses"],
)


# Cuerpo de la petición para crear un curso. organization_id va siempre explícito en el cuerpo, tanto si
# crea el curso un administrador como una organización: así hay un único contrato de API para ambos casos,
# y es el backend quien comprueba (más abajo) que una organización solo pueda indicar su propio id.
class CreateCourseRequest(BaseModel):
    organization_id: int
    course_name: str
    description: str
    teacher: str
    hours: int


# Cuerpo de la petición para matricular a un alumno en un curso.
class EnrollmentRequest(BaseModel):
    student_id: int


# Construye la respuesta del detalle de un curso.
def build_course_detail(course: Course, organization: Organization) -> dict:
    return {
        "course_id": course.id,
        "course_name": course.titulo,
        "teacher": course.docente,
        "hours": course.horas,
        "organization_id": organization.id,
        "organization_name": organization.nombre,
        "active": course.activo,
        "creation_date": course.fecha_creacion,
    }


# Endpoint para crear un curso. Solo puede hacerlo un administrador o una organización; un alumno no puede
# crear cursos. Un administrador puede crear cursos para cualquier organización; una organización solo
# puede crear cursos para sí misma (comprueba que organization_id coincide con su propio id).
@router.post("", status_code=201)
async def create_course_endpoint(
    request: CreateCourseRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede crear cursos")

    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        if request.organization_id != current_actor["actor_id"]:
            raise HTTPException(status_code=403, detail="Una organización solo puede crear cursos para sí misma")

    organization = get_organization_by_id(db, request.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organización no encontrada")

    if not request.course_name or not request.course_name.strip():
        raise HTTPException(status_code=400, detail="El nombre del curso es obligatorio")

    if not request.description or not request.description.strip():
        raise HTTPException(status_code=400, detail="La descripción del curso es obligatoria")

    if not request.teacher or not request.teacher.strip():
        raise HTTPException(status_code=400, detail="El docente es obligatorio")

    if request.hours <= 0:
        raise HTTPException(status_code=400, detail="Las horas deben ser mayores que cero")

    course = create_course(
        db,
        Course(
            organizacion_id=organization.id,
            titulo=request.course_name.strip(),
            descripcion=request.description.strip(),
            docente=request.teacher.strip(),
            horas=request.hours,
            activo=True,
        ),
    )

    return build_course_detail(course, organization)


# Endpoint para consultar el detalle de un curso. Accesible para administradores y organizaciones (sin
# restringir a la propia organización: el detalle no expone alumnos ni certificados); un alumno no puede usarlo.
@router.get("/{course_id}")
async def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede consultar el detalle de un curso")

    course = get_course_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    organization = get_organization_by_id(db, course.organizacion_id)
    if organization is None:
        raise HTTPException(
            status_code=500,
            detail=f"Organización asociada no encontrada (organizacion_id={course.organizacion_id})",
        )

    return build_course_detail(course, organization)


# Endpoint para listar los cursos visibles para el actor autenticado.
# Un administrador puede emitir certificados con cualquier curso, así que ve todos; una organización solo
# puede emitir con sus propios cursos, así que solo ve los suyos. Un alumno nunca puede emitir, así que no
# necesita este listado.
# Se incluye organization_id/organization_name de cada curso.
@router.get("")
async def get_courses(db: Session = Depends(get_db), current_actor: dict = Depends(get_current_actor)):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede consultar el listado de cursos")

    # Según el tipo de actor, se listan todos los cursos (administrador) o solo los de su propia organización.
    if current_actor["actor_type"] == ActorType.ADMINISTRATOR.value:
        courses = list_courses(db)
    else:
        courses = list_organization_courses(db, current_actor["actor_id"])

    # Se construye la respuesta cargando la organización de cada curso (necesaria para organization_name).
    summaries = []
    for course in courses:
        organization = get_organization_by_id(db, course.organizacion_id)
        if organization is None:
            raise HTTPException(
                status_code=500,
                detail=f"Organización asociada no encontrada (organizacion_id={course.organizacion_id})",
            )

        summaries.append({
            "course_id": course.id,
            "title": course.titulo,
            "organization_id": organization.id,
            "organization_name": organization.nombre,
        })

    return summaries


# Endpoint para listar los alumnos matriculados en un curso concreto (no todos los alumnos de la plataforma).
@router.get("/{course_id}/students")
async def get_course_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    course = get_course_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Un alumno nunca puede usar este endpoint (no puede emitir certificados).
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede consultar los alumnos matriculados en un curso")

    # Una organización solo puede consultar los alumnos de sus propios cursos (misma regla que en la emisión).
    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        if course.organizacion_id != current_actor["actor_id"]:
            raise HTTPException(status_code=403, detail="El curso no pertenece a la organización emisora")

    students = list_course_students(db, course_id)

    return [{"student_id": student.id, "full_name": f"{student.nombre} {student.apellidos}"} for student in students]


# Endpoint para matricular a un alumno en un curso. Solo puede hacerlo un administrador o una organización;
# un alumno no puede matricular alumnos. Una organización solo puede matricular en sus propios cursos.
@router.post("/{course_id}/students", status_code=201)
async def enroll_student(
    course_id: int,
    request: EnrollmentRequest,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede matricular alumnos")

    course = get_course_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Una organización solo puede matricular alumnos en sus propios cursos (misma regla que en la emisión).
    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        if course.organizacion_id != current_actor["actor_id"]:
            raise HTTPException(status_code=403, detail="El curso no pertenece a la organización emisora")

    student = get_student_by_id(db, request.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    if is_student_enrolled(db, request.student_id, course_id):
        raise HTTPException(status_code=400, detail="El alumno ya está matriculado en este curso")

    create_enrollment(db, CourseEnrollment(alumno_id=request.student_id, curso_id=course_id))

    return {"message": "Alumno matriculado correctamente"}


# Endpoint para eliminar la matrícula de un alumno en un curso. Solo puede hacerlo un administrador o una
# organización; un alumno no puede eliminar matrículas. Una organización solo puede hacerlo en sus propios cursos.
@router.delete("/{course_id}/students/{student_id}")
async def unenroll_student(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_actor: dict = Depends(get_current_actor),
):
    if current_actor["actor_type"] == ActorType.STUDENT.value:
        raise HTTPException(status_code=403, detail="Un alumno no puede eliminar matrículas")

    course = get_course_by_id(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Una organización solo puede eliminar matrículas de sus propios cursos (misma regla que en la emisión).
    if current_actor["actor_type"] == ActorType.ORGANIZATION.value:
        if course.organizacion_id != current_actor["actor_id"]:
            raise HTTPException(status_code=403, detail="El curso no pertenece a la organización emisora")

    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    enrollment = get_enrollment(db, student_id, course_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")

    delete_enrollment(db, enrollment)

    return {"message": "Alumno desmatriculado correctamente"}
