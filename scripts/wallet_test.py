# Script para probar la carga de la wallet y la generación de la dirección a partir de las claves.
from blockchain.wallet import (
    load_signing_key,
    load_verification_key,
    generate_address_from_key,
)

signing_key = load_signing_key()
verification_key = load_verification_key()
address = generate_address_from_key()

print(type(signing_key))
print(type(verification_key))

print("Dirección generada desde la clave:")
print(address)

print("Wallet cargada correctamente")