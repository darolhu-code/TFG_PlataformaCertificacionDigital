import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

PINATA_JWT = os.environ["PINATA_JWT"]
PINATA_UPLOAD_URL = os.environ["PINATA_UPLOAD_URL"]
PINATA_LIST_URL = os.environ["PINATA_LIST_URL"]
PINATA_GATEWAY_URL = os.environ["PINATA_GATEWAY_URL"]


# sube un archivo a Pinata dado el path local del archivo. Devuelve el CID del archivo subido
# (Por si se quiere subir un archivo ya guardado en el sistema de archivos).
def upload_to_pinata(file_path: Path) -> str:
    headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    with open(file_path, "rb") as file:
        files = {"file": (file_path.name, file, "application/pdf")}
        data = {"network": "public"}
        response = requests.post(PINATA_UPLOAD_URL, headers=headers, files=files, data=data)
    response.raise_for_status()
    result = response.json()
    cid = result["data"]["cid"]
    return cid

# Función para subir a Pinata/IPFS un contenido ya cargado en memoria (por ejemplo,
# el contenido de un UploadFile recibido en un endpoint de FastAPI) y devolver el CID resultante.
def upload_bytes_to_pinata(
    content: bytes,
    filename: str,
    content_type: str = "application/pdf",
) -> str:
    if not content:
        raise ValueError("El contenido no puede estar vacío")
    if not filename.strip():
        raise ValueError("El nombre del archivo no puede estar vacío")
    if content_type != "application/pdf":
        raise ValueError("Solo se permiten archivos PDF")

    headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    files = {"file": (filename, content, content_type)}
    data = {"network": "public"}
    response = requests.post(PINATA_UPLOAD_URL, headers=headers, files=files, data=data)
    response.raise_for_status()
    result = response.json()
    cid = result["data"]["cid"]
    return cid

# Descarga desde Pinata/IPFS el archivo asociado a un CID y devuelve su contenido en memoria (bytes).
def download_from_pinata(cid: str) -> bytes:
    if not cid.strip():
        raise ValueError("El CID no puede estar vacío")

    url = f"{PINATA_GATEWAY_URL}/{cid}"
    response = requests.get(url)
    response.raise_for_status()
    return response.content

# Consulta la lista de archivos subidos a Pinata y devuelve una lista con la información de cada archivo.
def list_pinata_files() -> list[dict]:
    headers = {"Authorization": f"Bearer {PINATA_JWT}"}
    response = requests.get(PINATA_LIST_URL, headers=headers)
    response.raise_for_status()
    result = response.json()
    return result["data"]["files"]