# Script de prueba para consultar información de Cardano a través de la API de Blockfrost
import os
from dotenv import load_dotenv
from blockchain.blockfrost import get_address, get_latest_block, get_transaction_metadata, get_utxos, verify_stored_certificate_integrity

load_dotenv(override=True)
CARDANO_ADDRESS = os.environ["CARDANO_ADDRESS"]

# consulta el último bloque de Cardano (preprod) y muestra la información relevante
def consultar_ultimo_bloque():
    try:
        block = get_latest_block()
    except Exception:
        print("Consulta a Blockfrost: KO")
        return

    print("=" * 30)
    print("Último bloque de Cardano (preprod)")
    print("=" * 30)
    print()
    print(f"Altura: {block.get('height')}")
    print(f"Hash: {block.get('hash')}")
    print(f"Slot: {block.get('slot')}")
    print(f"Época: {block.get('epoch')}")
    print(f"Nº transacciones: {block.get('tx_count')}")
    print()
    print("Consulta a Blockfrost: OK")


# consulta la información de la dirección de Cardano (preprod) y muestra el saldo en ADA, no tenemos en cuenta los TOKENS solo ADA
def consultar_direccion_cardano():
    try:
        info = get_address(CARDANO_ADDRESS)
    except Exception:
        print("Consulta a Blockfrost: KO")
        return

    lovelace = "0"
    for asset in info.get("amount", []):
        if asset["unit"] == "lovelace":
            lovelace = asset["quantity"]
            break
    ada = int(lovelace) / 1_000_000

    print("=" * 30)
    print("Información de la dirección de Cardano")
    print("=" * 30)
    print()
    print(f"Dirección: {CARDANO_ADDRESS}")
    print(f"Saldo: {ada} ADA")
    print()
    print("Consulta a Blockfrost: OK")


# pide un tx_hash por teclado, consulta sus metadatos en Cardano (preprod) y los muestra por pantalla
def consultar_metadata_transaccion():
    tx_hash = input("Introduce el tx_hash: ").strip()

    try:
        metadata = get_transaction_metadata(tx_hash)
    except Exception:
        print("Consulta a Blockfrost: KO")
        return

    if not metadata:
        print("La transacción no tiene metadatos.")
        return

    print("=" * 30)
    print("Metadatos de la transacción (CID y HASH del documento)")
    print("=" * 30)
    print()

    for entry in metadata:
        print(f"Label: {entry.get('label')}")
        print(f"Metadatos: {entry.get('json_metadata')}")
        print()

    print("Consulta a Blockfrost: OK")


# pide un tx_hash por teclado, verifica el certificado asociado (CID + SHA-256) y muestra el resultado
def verificar_certificado():
    tx_hash = input("Introduce el tx_hash: ").strip()

    try:
        result = verify_stored_certificate_integrity(tx_hash)
    except Exception:
        print("Verificación del certificado: KO")
        return

    print("=" * 30)
    print("Verificación del certificado")
    print("=" * 30)
    print()
    print("Transaction:")
    print(result["tx_hash"])
    print()
    print("CID:")
    print(result["cid"])
    print()
    print("SHA-256 registrado:")
    print(result["expected_sha256_hash"])
    print()
    print("SHA-256 calculado:")
    print(result["calculated_sha256_hash"])
    print()
    print("Resultado:")
    if result["is_valid"]:
        print("CERTIFICADO ÍNTEGRO")
    else:
        print("CERTIFICADO MODIFICADO")


# consulta los UTxOs de la dirección de Cardano (preprod) y los muestra por pantalla
def consultar_utxos():
    try:
        utxos = get_utxos(CARDANO_ADDRESS)
    except Exception:
        print("Consulta a Blockfrost: KO")
        return

    if not utxos:
        print("La dirección no tiene UTxOs.")
        return

    print("=" * 30)
    print("UTxOs de la dirección de Cardano")
    print("=" * 30)
    print()

    for utxo in utxos:
        print(f"Tx hash: {utxo.get('tx_hash')}")
        print(f"Índice de salida: {utxo.get('output_index')}")
        for asset in utxo["amount"]:
            if asset["unit"] == "lovelace":
                print(f"ADA: {int(asset['quantity']) / 1_000_000}")
            else:
                print(f"Token: {asset['unit']}")
                print(f"Cantidad: {asset['quantity']}")
        print()

    print("Consulta a Blockfrost: OK")