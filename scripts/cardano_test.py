# Script de prueba para crear y enviar una transacción a la red de Cardano a través de Blockfrost
from blockchain.cardano import get_chain_context
from blockchain.wallet import CARDANO_ADDRESS, load_signing_key
from pycardano import (
    TransactionBuilder,
    TransactionOutput,
    Value,
    Address,
)

ENVIAR = False  # Cambiar a True para enviar la transacción a la red de Cardano a través de Blockfrost

# representa la conexión con Cardano a través de Blockfrost
context = get_chain_context()
print("Conexión con Cardano correcta")


# Consulta los UTxOs de la dirección de Cardano y los muestra por pantalla. 
# Método de PyCardano.
utxos = context.utxos(CARDANO_ADDRESS)
print(f"UTxOs encontrados: {len(utxos)}")
for utxo in utxos:
    print(utxo)


# Se crea una transacción de ejemplo: en este caso se envía 50 ADA a la misma dirección de Cardano que tenemos en el .env
# representa el constructor de transacciones de Cardano, se utiliza para crear y firmar transacciones
builder = TransactionBuilder(context)

# agrega los UTxOs de la dirección de Cardano al constructor de transacciones, el que mejor se adapte a la transacción que queremos realizar.
builder.add_input_address(
    Address.from_primitive(CARDANO_ADDRESS)
)
# agrega una salida a la transacción, en este caso se envía 50 ADA a la misma dirección de Cardano que tenemos en el .env
builder.add_output(
    TransactionOutput(
        Address.from_primitive(CARDANO_ADDRESS),
        Value(50_000_000),  # 50 ADA
    )
)

# Carga la clave privada (payment.skey) que se utilizará para firmar la transacción
signing_key = load_signing_key()

# Construye la transacción, selecciona automáticamente los UTxOs necesarios,
# calcula la comisión, genera el cambio y firma la transacción.
signed_tx = builder.build_and_sign(
    signing_keys=[signing_key],
    change_address=Address.from_primitive(CARDANO_ADDRESS),
)

print("\n========== RESUMEN DE LA TRANSACCIÓN ==========")
print(f"Tx Hash: {signed_tx.transaction_body.hash().hex()}")
print(f"Fee: {signed_tx.transaction_body.fee} lovelace")
print(f"Inputs: {len(signed_tx.transaction_body.inputs)}")
print(f"Outputs: {len(signed_tx.transaction_body.outputs)}")


# una vez que la transacción está construida y firmada, se envía a la red de Cardano a través de Blockfrost
# usamos el método submit_tx del contexto de la cadena de bloques para enviar la transacción firmada a la red de Cardano a través de Blockfrost
if ENVIAR:
    context.submit_tx(signed_tx)
    print("\nTransacción enviada correctamente")
    print(f"Tx Hash: {signed_tx.transaction_body.hash().hex()}")
else:
    print("\nTransacción construida pero NO enviada")