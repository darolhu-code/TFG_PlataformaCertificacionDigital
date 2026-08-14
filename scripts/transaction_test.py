# Script para crear, firmar y enviar una transacción a la red de Cardano a través de Blockfrost, incluyendo metadatos (CID y hash SHA256) en la transacción.
from blockchain.transaction import (
    create_signed_transaction,
    get_transaction_info,
    submit_transaction
)

from blockchain.wallet import CARDANO_ADDRESS

ENVIAR = False  # Cambiar a True para enviar la transacción a la red de Cardano (preprod) a través de Blockfrost
DESTINATION = CARDANO_ADDRESS
AMOUNT = 50_000_000  # 50 ADA


# Crea, firma y envía una transacción desde la wallet del backend (CARDANO_ADDRESS) hacia DESTINATION. Devuelve el hash de la transacción en formato hexadecimal
# Incluimos metadatos de ejemplo (CID y hash SHA256) en la transacción, que se pueden utilizar para verificar la integridad del documento.
signed_tx = create_signed_transaction(
    DESTINATION,
    AMOUNT,
    cid="QmPruebaCID123456789",
    sha256_hash="abcdef1234567890",
)

# Obtiene un resumen de la transacción firmada (no enviada todavía).
info = get_transaction_info(signed_tx)

print("\n========== INFORMACIÓN DE LA TRANSACCIÓN ==========")
print(f"Tx Hash: {info['tx_hash']}")
print(f"Fee: {info['fee']} lovelace")
print(f"Inputs: {len(info['inputs'])}")
print(f"Outputs: {len(info['outputs'])}")

if ENVIAR:
    tx_hash = submit_transaction(signed_tx)
    print("\nTransacción enviada correctamente")
    print(f"Tx Hash: {tx_hash}")
else:
    print("\nTransacción construida pero NO enviada")