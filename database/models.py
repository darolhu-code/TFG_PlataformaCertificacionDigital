import enum
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


# Estado del registro de un certificado en Cardano
class CertificateStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ERROR = "ERROR"


# Modelo que representa a un alumno de la plataforma
class Student(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dni: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Modelo que representa a una organización emisora de certificados
class Organization(Base):
    __tablename__ = "organizaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Modelo que representa a un administrador de la plataforma
class Administrator(Base):
    __tablename__ = "administradores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dni: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Modelo que representa los permisos que otorga un usuario a una organización para poder ver todos sus certificados, aunque los haya emitido otra organización
# distinta.
class AccessPermission(Base):
    __tablename__ = "permisos_acceso"
    __table_args__ = (UniqueConstraint("alumno_id", "organizacion_id", name="uq_permisos_acceso_alumno_organizacion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"), nullable=False)
    organizacion_id: Mapped[int] = mapped_column(ForeignKey("organizaciones.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Modelo que representa un curso formativo impartido por una organización
class Course(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacion_id: Mapped[int] = mapped_column(ForeignKey("organizaciones.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    docente: Mapped[str] = mapped_column(String(255), nullable=False)
    horas: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# Modelo que representa la matrícula de un alumno en un curso. 
# Sin esta tabla, cualquier alumno podría recibir un certificado de cualquier curso.
class CourseEnrollment(Base):
    __tablename__ = "matriculas"
    # Impide matricular dos veces al mismo alumno en el mismo curso (una fila = una matrícula, sin duplicados).
    __table_args__ = (UniqueConstraint("alumno_id", "curso_id", name="uq_matriculas_alumno_curso"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"), nullable=False)
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Modelo que representa un certificado registrado en Cardano/IPFS
class Certificate(Base):
    __tablename__ = "certificados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"), nullable=False)
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"), nullable=False)
    organizacion_emisora_id: Mapped[int] = mapped_column(ForeignKey("organizaciones.id"), nullable=False)
    nombre_certificado: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo_contenido: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cid: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tx_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    fecha_registro_cardano: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estado_registro: Mapped[CertificateStatus] = mapped_column(
        Enum(CertificateStatus, name="estado_registro"), default=CertificateStatus.PENDING, nullable=False
    )
    revocado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Motivo y fecha de la revocación; ambos solo tienen valor cuando revocado=True.
    motivo_revocacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_revocacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
