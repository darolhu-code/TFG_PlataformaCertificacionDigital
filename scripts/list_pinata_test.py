# Script para listar los certificados subidos a Pinata y descargar un certificado desde Pinata/IPFS.
from pathlib import Path

from storage.pinata import download_from_pinata, list_pinata_files

DOWNLOAD_PATH = Path("docs/certificado_descargado.pdf")

# lista los certificados subidos a Pinata/IPFS y los muestra por pantalla
def listar_certificados_pinata():
    try:
        files = list_pinata_files()
    except Exception:
        print("Lectura de IPFS: KO")
        return

    if not files:
        print("No hay ficheros subidos a Pinata.")
        return

    print("=" * 30)
    print("Ficheros subidos a Pinata")
    print("=" * 30)
    print()

    for file in files:
        print(f"Archivo: {file.get('name')}")
        print(f"CID: {file.get('cid')}")
        print(f"Fecha de subida: {file.get('created_at')}")
        print()

    print("Lectura de IPFS: OK")


# pide un CID por consola, descarga el certificado desde Pinata/IPFS y lo guarda en docs/
def descargar_certificado_pinata():
    cid = input("Introduce el CID: ").strip()

    try:
        content = download_from_pinata(cid)
    except Exception:
        print("Descarga de IPFS: KO")
        return

    DOWNLOAD_PATH.parent.mkdir(exist_ok=True)
    DOWNLOAD_PATH.write_bytes(content)

    print("=" * 30)
    print("Certificado descargado")
    print("=" * 30)
    print()
    print(f"CID: {cid}")
    print(f"Bytes descargados: {len(content)}")
    print(f"Guardado en: {DOWNLOAD_PATH}")
    print()
    print("Descarga de IPFS: OK")
