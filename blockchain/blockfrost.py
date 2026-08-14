import os
import requests
from dotenv import load_dotenv

from blockchain.transaction import CARDANO_DOCUMENT_METADATA_LABEL
from storage.crypto import decrypt_bytes
from storage.pinata import download_from_pinata
from utils.hash import compute_sha256_bytes

load_dotenv()
BLOCKFROST_API_KEY = os.environ["BLOCKFROST_API_KEY"]
BLOCKFROST_BASE_URL = os.environ["BLOCKFROST_BASE_URL"]

#Obtiene la información del último bloque de Cardano
def get_latest_block() -> dict:
    headers = {"project_id": BLOCKFROST_API_KEY}
    response = requests.get(f"{BLOCKFROST_BASE_URL}/blocks/latest", headers=headers)
    response.raise_for_status()
    return response.json()

#Obtiene la información de una dirección de Cardano - Wallet
def get_address(address: str) -> dict:
    headers = {"project_id": BLOCKFROST_API_KEY}
    response = requests.get(f"{BLOCKFROST_BASE_URL}/addresses/{address}", headers=headers)
    response.raise_for_status()
    return response.json()

#Obtiene los UTxOs asociados a una dirección de Cardano
def get_utxos(address: str) -> list[dict]:
    headers = {"project_id": BLOCKFROST_API_KEY}
    response = requests.get(f"{BLOCKFROST_BASE_URL}/addresses/{address}/utxos", headers=headers)
    response.raise_for_status()
    return response.json()

#Obtiene los metadatos asociados a una transacción de Cardano
def get_transaction_metadata(tx_hash: str) -> list[dict]:
    if not tx_hash.strip():
        raise ValueError("El tx_hash no puede estar vacío")

    headers = {"project_id": BLOCKFROST_API_KEY}
    response = requests.get(f"{BLOCKFROST_BASE_URL}/txs/{tx_hash}/metadata", headers=headers)
    response.raise_for_status()
    return response.json()

# Función que extrae de los metadatos de la transacción el CID y el SHA-256 registrados en Cardano.
def get_registered_certificate_metadata(tx_hash: str) -> dict:
    metadata = get_transaction_metadata(tx_hash)

    document_metadata = None
    for entry in metadata:
        if entry.get("label") == str(CARDANO_DOCUMENT_METADATA_LABEL):
            document_metadata = entry.get("json_metadata")
            break

    if document_metadata is None:
        raise ValueError("La transacción no contiene metadata de un certificado")

    return {
        "cid": document_metadata["cid"],
        "sha256_hash": document_metadata["sha256_hash"],
    }

# Descarga de IPFS el certificado almacenado y comprueba que su SHA-256
# sigue coincidiendo con el registrado en Cardano. No requiere ningún archivo del usuario.
def verify_stored_certificate_integrity(tx_hash: str) -> dict:
    registered_metadata = get_registered_certificate_metadata(tx_hash)
    cid = registered_metadata["cid"]
    expected_sha256_hash = registered_metadata["sha256_hash"]

    # El contenido en IPFS está cifrado; hay que descifrarlo para obtener el PDF
    # original, que es sobre el que se calculó el SHA-256 registrado en Cardano.
    encrypted_content = download_from_pinata(cid)
    stored_content = decrypt_bytes(encrypted_content)
    calculated_sha256_hash = compute_sha256_bytes(stored_content)

    return {
        "tx_hash": tx_hash,
        "cid": cid,
        "expected_sha256_hash": expected_sha256_hash,
        "calculated_sha256_hash": calculated_sha256_hash,
        "is_valid": calculated_sha256_hash == expected_sha256_hash,
    }

# Calcula el SHA-256 de un PDF aportado por el usuario y lo compara con
# el registrado en Cardano, sin necesidad de consultar IPFS.
def verify_uploaded_certificate_integrity(tx_hash: str, uploaded_content: bytes) -> dict:
    registered_metadata = get_registered_certificate_metadata(tx_hash)
    expected_sha256_hash = registered_metadata["sha256_hash"]
    uploaded_sha256_hash = compute_sha256_bytes(uploaded_content)

    return {
        "tx_hash": tx_hash,
        "expected_sha256_hash": expected_sha256_hash,
        "uploaded_sha256_hash": uploaded_sha256_hash,
        "is_valid": uploaded_sha256_hash == expected_sha256_hash,
    }
