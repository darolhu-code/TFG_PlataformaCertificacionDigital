import hashlib
from pathlib import Path

# Calcula el SHA-256 de un archivo dado su path. 
# Por si se quiere calcular el hash de un archivo guardado en una carperta del sistema.
def compute_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


# Calcula el SHA-256 de un contenido cargado en memoria (el contenido de un UploadFile recibido en el endpoint de FastAPI).
def compute_sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()