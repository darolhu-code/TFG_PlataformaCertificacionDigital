from sqlalchemy.orm import Session

from database.models import AccessPermission, Administrator, Certificate, Course, CourseEnrollment, Organization, Student


# crea un nuevo alumno en la base de datos
def create_student(db: Session, student: Student) -> Student:
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


# crea una nueva organización en la base de datos
def create_organization(db: Session, organization: Organization) -> Organization:
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


# crea un nuevo administrador en la base de datos
def create_administrator(db: Session, administrator: Administrator) -> Administrator:
    db.add(administrator)
    db.commit()
    db.refresh(administrator)
    return administrator


# crea un nuevo curso en la base de datos
def create_course(db: Session, course: Course) -> Course:
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


# crea un nuevo certificado en la base de datos
def create_certificate(db: Session, certificate: Certificate) -> Certificate:
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


# crea una nueva matrícula (relación alumno-curso) en la base de datos
def create_enrollment(db: Session, enrollment: CourseEnrollment) -> CourseEnrollment:
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


# obtiene un alumno a partir de su id
def get_student_by_id(db: Session, student_id: int) -> Student | None:
    return db.get(Student, student_id)


# obtiene un alumno a partir de su email, utilizado en el login
def get_student_by_email(db: Session, email: str) -> Student | None:
    return db.query(Student).filter(Student.email == email).first()


# obtiene un alumno a partir de su DNI, utilizado para comprobar que no exista ya al crear uno nuevo
def get_student_by_dni(db: Session, dni: str) -> Student | None:
    return db.query(Student).filter(Student.dni == dni).first()


# lista todos los alumnos de la plataforma, sin filtrar
def list_students(db: Session) -> list[Student]:
    return db.query(Student).all()


# obtiene un curso a partir de su id
def get_course_by_id(db: Session, course_id: int) -> Course | None:
    return db.get(Course, course_id)


# obtiene una organización a partir de su id
def get_organization_by_id(db: Session, organization_id: int) -> Organization | None:
    return db.get(Organization, organization_id)


# obtiene una organización a partir de su email, utilizado en el login
def get_organization_by_email(db: Session, email: str) -> Organization | None:
    return db.query(Organization).filter(Organization.email == email).first()


# lista todas las organizaciones de la plataforma, sin filtrar.
def list_organizations(db: Session) -> list[Organization]:
    return db.query(Organization).all()


# obtiene un administrador a partir de su id
def get_administrator_by_id(db: Session, administrator_id: int) -> Administrator | None:
    return db.get(Administrator, administrator_id)


# obtiene un administrador a partir de su email, utilizado en el login
def get_administrator_by_email(db: Session, email: str) -> Administrator | None:
    return db.query(Administrator).filter(Administrator.email == email).first()


# obtiene un administrador a partir de su DNI, utilizado para comprobar que no exista ya al crear uno nuevo
def get_administrator_by_dni(db: Session, dni: str) -> Administrator | None:
    return db.query(Administrator).filter(Administrator.dni == dni).first()


# lista todos los administradores de la plataforma, sin filtrar
def list_administrators(db: Session) -> list[Administrator]:
    return db.query(Administrator).all()


# obtiene un certificado a partir de su id
def get_certificate_by_id(db: Session, certificate_id: int) -> Certificate | None:
    return db.get(Certificate, certificate_id)


# lista todos los cursos de la plataforma, sin filtrar por organización. Pensado para un administrador,
# que puede emitir certificados con cualquier curso, sin importar qué organización lo imparte.
def list_courses(db: Session) -> list[Course]:
    return db.query(Course).all()


# lista únicamente los cursos de una organización concreta. Pensado para una organización, que solo puede
# emitir certificados con sus propios cursos (misma regla que ya valida upload_certificate).
def list_organization_courses(db: Session, organization_id: int) -> list[Course]:
    return db.query(Course).filter(Course.organizacion_id == organization_id).all()


# lista todos los certificados ordenados del más reciente al más antiguo
def list_certificates(db: Session) -> list[Certificate]:
    return db.query(Certificate).order_by(Certificate.fecha_creacion.desc()).all()


# lista todos los certificados de un alumno, ordenados del más reciente al más antiguo
def list_student_certificates(db: Session, student_id: int) -> list[Certificate]:
    return (
        db.query(Certificate)
        .filter(Certificate.alumno_id == student_id)
        .order_by(Certificate.fecha_creacion.desc())
        .all()
    )


# lista todos los certificados emitidos por una organización, ordenados del más reciente al más antiguo
def list_organization_certificates(db: Session, organization_id: int) -> list[Certificate]:
    return (
        db.query(Certificate)
        .filter(Certificate.organizacion_emisora_id == organization_id)
        .order_by(Certificate.fecha_creacion.desc())
        .all()
    )


# lista los certificados de los alumnos que han concedido permiso activo a una organización.
# Dos consultas simples (permisos, luego certificados) en vez de un JOIN, para mantenerlo fácil de leer.
def list_permitted_certificates(db: Session, organization_id: int) -> list[Certificate]:
    # obtenemos los IDs de los alumnos que han concedido permiso activo a la organización
    permitted_student_ids = [
        row.alumno_id
        for row in db.query(AccessPermission.alumno_id)
        .filter(AccessPermission.organizacion_id == organization_id, AccessPermission.activo.is_(True))
        .all()
    ]

    if not permitted_student_ids:
        return []
    # obtenemos los certificados de esos alumnos
    return db.query(Certificate).filter(Certificate.alumno_id.in_(permitted_student_ids)).all()


# actualiza un certificado ya existente en la base de datos
def update_certificate(db: Session, certificate: Certificate) -> Certificate:
    db.commit()
    db.refresh(certificate)
    return certificate


# elimina un certificado de la base de datos
def delete_certificate(db: Session, certificate: Certificate) -> None:
    db.delete(certificate)
    db.commit()





# Gestión de permisos - reglas de acceso a certificados: 
# - El alumno ve siempre sus propios certificados.
# - Una organización ve los certificados que ella misma emitió, así como los de cualquier alumno que le haya dado acceso a sus certificados.
# - Un administrador ve todos los certificados de la plataforma.

# Concede permiso a una organización para ver todos los certificados de un alumno; si ya existía (en estado inactivo), lo reactiva
def grant_permission(db: Session, student_id: int, organization_id: int) -> AccessPermission:
    student = get_student_by_id(db, student_id)
    if student is None:
        raise ValueError(f"Alumno no encontrado (alumno_id={student_id})")

    organization = get_organization_by_id(db, organization_id)
    if organization is None:
        raise ValueError(f"Organización no encontrada (organizacion_id={organization_id})")

    permission = (
        db.query(AccessPermission)
        .filter(AccessPermission.alumno_id == student_id, AccessPermission.organizacion_id == organization_id)
        .first()
    )

    if permission is None:
        permission = AccessPermission(alumno_id=student_id, organizacion_id=organization_id, activo=True)
        db.add(permission)
    elif not permission.activo:
        permission.activo = True

    db.commit()
    db.refresh(permission)
    return permission


# revoca el permiso de una organización sobre los certificados de un alumno, sin borrar la fila (activo=False)
def revoke_permission(db: Session, student_id: int, organization_id: int) -> AccessPermission | None:
    permission = (
        db.query(AccessPermission)
        .filter(AccessPermission.alumno_id == student_id, AccessPermission.organizacion_id == organization_id)
        .first()
    )

    if permission is None:
        return None

    permission.activo = False
    db.commit()
    db.refresh(permission)
    return permission


# comprueba si una organización tiene actualmente permiso activo sobre los certificados de un alumno
def has_permission(db: Session, student_id: int, organization_id: int) -> bool:
    permission = (
        db.query(AccessPermission)
        .filter(
            AccessPermission.alumno_id == student_id,
            AccessPermission.organizacion_id == organization_id,
            AccessPermission.activo.is_(True),
        )
        .first()
    )
    return permission is not None


# lista los permisos activos que los alumnos han concedido a una organización concreta (vista de solo lectura para esa organización)
def list_organization_permissions(db: Session, organization_id: int) -> list[AccessPermission]:
    return (
        db.query(AccessPermission)
        .filter(AccessPermission.organizacion_id == organization_id, AccessPermission.activo.is_(True))
        .all()
    )


# lista todos los permisos activos de la plataforma (vista de solo lectura para un administrador)
def list_all_active_permissions(db: Session) -> list[AccessPermission]:
    return db.query(AccessPermission).filter(AccessPermission.activo.is_(True)).all()


# lista las organizaciones a las que un alumno ha concedido permiso activo
def list_user_permissions(db: Session, student_id: int) -> list[Organization]:
    return (
        db.query(Organization)
        .join(AccessPermission, AccessPermission.organizacion_id == Organization.id)
        .filter(AccessPermission.alumno_id == student_id, AccessPermission.activo.is_(True))
        .all()
    )

# comprueba si un alumno está matriculado en un curso concreto; se usa en la emisión para validar la relación
# alumno-curso
def is_student_enrolled(db: Session, student_id: int, course_id: int) -> bool:
    enrollment = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.alumno_id == student_id, CourseEnrollment.curso_id == course_id)
        .first()
    )
    return enrollment is not None


# obtiene la matrícula de un alumno en un curso concreto, si existe (para poder eliminarla)
def get_enrollment(db: Session, student_id: int, course_id: int) -> CourseEnrollment | None:
    return (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.alumno_id == student_id, CourseEnrollment.curso_id == course_id)
        .first()
    )


# elimina una matrícula (desmatricula a un alumno de un curso)
def delete_enrollment(db: Session, enrollment: CourseEnrollment) -> None:
    db.delete(enrollment)
    db.commit()


# lista los alumnos matriculados en un curso concreto
def list_course_students(db: Session, course_id: int) -> list[Student]:
    return (
        db.query(Student)
        .join(CourseEnrollment, CourseEnrollment.alumno_id == Student.id)
        .filter(CourseEnrollment.curso_id == course_id)
        .all()
    )
