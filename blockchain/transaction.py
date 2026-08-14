import time

from blockchain.cardano import get_chain_context
from blockchain.wallet import CARDANO_ADDRESS, load_signing_key
from pycardano import (
    Address,
    Transaction,
    TransactionBuilder,
    TransactionOutput,
    Value,
)
from pycardano.exception import TransactionFailedException
from pycardano.metadata import (
    Metadata,
    AlonzoMetadata,
    AuxiliaryData,
)

# Label de los metadatos utilizados para almacenar el CID y el SHA-256 del documento en la blockchain de Cardano.
CARDANO_DOCUMENT_METADATA_LABEL = 2026

# Si se emiten dos certificados muy seguidos, la wallet puede intentar gastar un UTxO que una transacción
# anterior ya gastó pero que todavía no se ha confirmado en un bloque ("All inputs are spent"). Estos valores
# controlan cuántas veces se reintenta la emisión y cuánto se espera entre intentos para dar tiempo a esa confirmación.
TRANSACTION_MAX_RETRIES = 3
TRANSACTION_RETRY_DELAY_SECONDS = 15


# crea y firma una transacción documental con metadatos (CID y hash SHA256) desde la wallet del backend (CARDANO_ADDRESS) hacia destination_address. Devuelve la transacción firmada.
def create_signed_transaction(destination_address: str, amount_lovelace: int, cid: str, sha256_hash: str) -> Transaction:
    context = get_chain_context()
    signing_key = load_signing_key()
    wallet_address = Address.from_primitive(CARDANO_ADDRESS)

    # Validación de los parámetros de entrada
    if not destination_address.strip():
        raise ValueError("La dirección de destino no puede estar vacía")
    if amount_lovelace <= 0:
        raise ValueError("El importe en lovelace debe ser mayor que cero")
    if not cid.strip():
        raise ValueError("El CID no puede estar vacío")
    if not sha256_hash.strip():
        raise ValueError("El SHA-256 no puede estar vacío")

    # Se construyen los metadatos de la transacción y se añaden al constructor de transacciones.
    auxiliary_data = build_document_metadata(cid=cid, sha256_hash=sha256_hash)

    # representa el constructor de transacciones de Cardano, se utiliza para crear y firmar transacciones
    builder = TransactionBuilder(context=context, auxiliary_data=auxiliary_data)

    # Selecciona automáticamente los UTxOs de la wallet necesarios para cubrir el importe y la comisión.
    builder.add_input_address(wallet_address)

    builder.add_output(
        TransactionOutput(
            Address.from_primitive(destination_address),
            Value(amount_lovelace),
        )
    )

    # build_and_sign() calcula la comisión, genera el cambio (devuelto a
    # change_address) y firma la transacción en un solo paso.
    signed_tx = builder.build_and_sign(
        signing_keys=[signing_key],
        change_address=wallet_address,
    )
    return signed_tx


# Construye los metadatos de la transacción: contiene el CID y el hash SHA256 del documento.
def build_document_metadata(cid: str, sha256_hash: str) -> AuxiliaryData:
    metadata = Metadata()

    metadata[CARDANO_DOCUMENT_METADATA_LABEL] = {
        "cid": cid,
        "sha256_hash": sha256_hash,
    }
    return AuxiliaryData(
        AlonzoMetadata(
            metadata=metadata
        )
    )

# Envía una transacción ya firmada a la red de Cardano a través de
# Blockfrost y devuelve el hash de la transacción en formato hexadecimal.
# get_chain_context() obtiene el contexto de la cadena de bloques de Cardano a través de Blockfrost y permite enviar la transacción firmada a la red.
def submit_transaction(signed_tx: Transaction) -> str:
    context = get_chain_context()
    context.submit_tx(signed_tx)
    return signed_tx.transaction_body.hash().hex()


# Crea, firma y envía una transacción desde la wallet del backend (CARDANO_ADDRESS) hacia destination_address.
# Si falla por colisión de UTxOs (ver TRANSACTION_MAX_RETRIES arriba), se reintenta reconstruyendo la
# transacción desde cero en cada intento: hay que volver a consultar qué UTxOs siguen disponibles, no basta
# con reenviar la misma transacción firmada.
# Devuelve el hash de la transacción en formato hexadecimal.
def send_transaction(destination_address: str, amount_lovelace: int, cid: str, sha256_hash: str) -> str:
    for attempt in range(TRANSACTION_MAX_RETRIES):
        signed_tx = create_signed_transaction(
            destination_address=destination_address,
            amount_lovelace=amount_lovelace,
            cid=cid,
            sha256_hash=sha256_hash
        )

        try:
            return submit_transaction(signed_tx)
        except TransactionFailedException as error:
            # Solo se reintenta si el fallo es justo esa colisión de UTxOs; cualquier otro motivo (fondos
            # insuficientes, red caída...) se propaga de inmediato, sin desperdiciar reintentos ni esperas.
            is_utxo_collision = "All inputs are spent" in str(error)
            if not is_utxo_collision or attempt == TRANSACTION_MAX_RETRIES - 1:
                raise

            time.sleep(TRANSACTION_RETRY_DELAY_SECONDS)


# Devuelve un resumen de una transacción firmada.
def get_transaction_info(signed_tx: Transaction) -> dict:
    body = signed_tx.transaction_body
    return {
        "tx_hash": body.hash().hex(),
        "fee": body.fee,
        "inputs": body.inputs,
        "outputs": body.outputs,
    }