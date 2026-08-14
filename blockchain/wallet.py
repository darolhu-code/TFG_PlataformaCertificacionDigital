import os
from dotenv import load_dotenv
from pathlib import Path
from pycardano import (
    PaymentSigningKey,
    PaymentVerificationKey,
    Address,
    Network,
)


WALLET_DIR = Path("wallet")
SKEY_PATH = WALLET_DIR / "payment.skey"
VKEY_PATH = WALLET_DIR / "payment.vkey"

# En Render la wallet no está en el repositorio (ver .gitignore): las claves se suben como Secret Files,
# que Render monta siempre en esta carpeta fija.
RENDER_SECRETS_DIR = Path("/etc/secrets")
RENDER_SKEY_PATH = RENDER_SECRETS_DIR / "payment.skey"
RENDER_VKEY_PATH = RENDER_SECRETS_DIR / "payment.vkey"

load_dotenv()
CARDANO_ADDRESS = os.environ["CARDANO_ADDRESS"]


# Resuelve qué ruta usar para la clave de la wallet: 
# la de wallet/ si existe (ejecución en local), o Secret Files para Render.
def resolve_key_path(local_path: Path, render_path: Path) -> Path:
    if local_path.exists():
        return local_path
    return render_path


# Carga la clave de firma de la wallet desde el archivo payment.skey
def load_signing_key() -> PaymentSigningKey:
    return PaymentSigningKey.load(str(resolve_key_path(SKEY_PATH, RENDER_SKEY_PATH)))

# Carga la clave de verificación de la wallet desde el archivo payment.vkey
def load_verification_key() -> PaymentVerificationKey:
    return PaymentVerificationKey.load(str(resolve_key_path(VKEY_PATH, RENDER_VKEY_PATH)))

# Genera la dirección de Cardano a partir de la clave de verificación, esto es para asegurarnos que la dirección generada es la misma que la que tenemos en el .env
def generate_address_from_key() -> Address:
    verification_key = load_verification_key()

    return Address(
        payment_part=verification_key.hash(),
        network=Network.TESTNET,
    )