# Script para subir un certificado PDF a Pinata/IPFS y mostrar el hash SHA256 y el CID resultante.
import os
from pathlib import Path
from dotenv import load_dotenv
from storage.pinata import upload_to_pinata
from utils.hash import compute_sha256


load_dotenv()
PDF_FOLDER = os.environ["PDF_FOLDER"]

# Busca el primer PDF en la carpeta especificada y devuelve su ruta como un objeto Path. Si no se encuentra ningún PDF, lanza una excepción FileNotFoundError.
def encontrar_pdf_carpeta(folder: str) -> Path:
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".pdf"):
            return Path(folder) / name
    raise FileNotFoundError(f"No se ha encontrado ningún PDF en {folder}")

# Sube un certificado PDF a Pinata/IPFS y muestra el hash SHA256 y el CID resultante. 
# Si no se encuentra ningún PDF en la carpeta especificada, lanza una excepción FileNotFoundError.
def subir_certificado_pinata():
    pdf_path = encontrar_pdf_carpeta(PDF_FOLDER)
    pdf_hash = compute_sha256(pdf_path)

    try:
        cid = upload_to_pinata(pdf_path)
    except Exception:
        print("Subida a IPFS: KO")
        return

    print("=" * 30)
    print("Certificado procesado")
    print("=" * 30)
    print()
    print("Archivo:")
    print(pdf_path.name)
    print()
    print("SHA-256:")
    print(pdf_hash)
    print()
    print("CID:")
    print(cid)
    print()
    print("Subida a IPFS: OK")
