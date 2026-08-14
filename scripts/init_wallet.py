# Script para inicializar la wallet del backend. Si ya existe, no hace nada. Si no existe, genera una nueva wallet.
from pathlib import Path

from pycardano import Address, Network, PaymentKeyPair

WALLET_DIR = Path("wallet")
SKEY_PATH = WALLET_DIR / "payment.skey"
VKEY_PATH = WALLET_DIR / "payment.vkey"
ADDRESS_PATH = WALLET_DIR / "address.txt"

# Genera una nueva wallet de Cardano (preprod) y guarda la clave de firma, la clave de verificación y la dirección en archivos dentro del directorio wallet.
def generar_wallet() -> Address:
    WALLET_DIR.mkdir(exist_ok=True)

    key_pair = PaymentKeyPair.generate()
    key_pair.signing_key.save(str(SKEY_PATH))
    key_pair.verification_key.save(str(VKEY_PATH))

    address = Address(
        payment_part=key_pair.verification_key.hash(),
        network=Network.TESTNET,  # Preprod utiliza el mismo network id que Testnet
    )
    ADDRESS_PATH.write_text(str(address))
    return address


# Inicializa la wallet del backend. Si ya existe, no hace nada. Si no existe, genera una nueva wallet y guarda la dirección en un archivo.
def inicializar_wallet():
    wallet_exists = (
        SKEY_PATH.exists()
        and VKEY_PATH.exists()
        and ADDRESS_PATH.exists()
    )
    
    if wallet_exists:
        print("La wallet ya existe.")
    else:
        print("No existe wallet. Generando wallet del backend...")
        generar_wallet()

        address = generar_wallet()
        print("Wallet creada correctamente.")
        print(f"Dirección generada: {address}")


if __name__ == "__main__":
    inicializar_wallet()
