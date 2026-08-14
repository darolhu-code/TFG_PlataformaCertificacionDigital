# Módulo de cifrado simétrico (AES-256-GCM) para los certificados antes de subirlos a IPFS.
# El SHA-256 se calcula siempre sobre el PDF original, antes de cifrar; solo el contenido
# cifrado se sube a Pinata/IPFS, y se descifra de nuevo al recuperarlo desde ahí.

import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv


load_dotenv()
# La clave de cifrado se obtiene de la variable de entorno CERTIFICATE_ENCRYPTION_KEY, que debe contener una cadena base64 de 32 bytes (256 bits) para AES-256.
CERTIFICATE_ENCRYPTION_KEY = base64.b64decode(os.environ["CERTIFICATE_ENCRYPTION_KEY"])

# Tamaño estándar del nonce en AES-GCM (96 bits).
NONCE_SIZE_BYTES = 12

# Cifra el contenido con AES-256-GCM. El nonce se genera aleatoriamente en cada
# llamada y se antepone al texto cifrado para poder recuperarlo al descifrar.
def encrypt_bytes(content: bytes) -> bytes:
    aesgcm = AESGCM(CERTIFICATE_ENCRYPTION_KEY)
    nonce = os.urandom(NONCE_SIZE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, content, None)
    return nonce + ciphertext

# Descifra un contenido generado por encrypt_bytes(). GCM comprueba automáticamente
# la autenticidad del contenido y lanza una excepción si detecta cualquier alteración.
def decrypt_bytes(encrypted_content: bytes) -> bytes:
    nonce = encrypted_content[:NONCE_SIZE_BYTES]
    ciphertext = encrypted_content[NONCE_SIZE_BYTES:]
    aesgcm = AESGCM(CERTIFICATE_ENCRYPTION_KEY)
    return aesgcm.decrypt(nonce, ciphertext, None)
