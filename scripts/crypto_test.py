# Script de prueba para cifrar y descifrar un PDF utilizando las funciones de cifrado implementadas en storage/cripto.py
import os
from dotenv import load_dotenv
from storage.crypto import decrypt_bytes, encrypt_bytes

load_dotenv()
PDF_FOLDER = os.environ["PDF_FOLDER"]

# cifra y descifra un PDF de prueba y comprueba que el contenido recuperado es idéntico al original
def prueba_cifrado():
    pdf_path = os.path.join(PDF_FOLDER, "Certificado.pdf")

    with open(pdf_path, "rb") as file:
        original_pdf = file.read()

    encrypted_content = encrypt_bytes(original_pdf)
    recovered_pdf = decrypt_bytes(encrypted_content)

    print("=" * 30)
    print("Prueba de cifrado y descifrado")
    print("=" * 30)
    print()
    print(f"Tamaño original: {len(original_pdf)} bytes")
    print(f"Tamaño cifrado: {len(encrypted_content)} bytes")
    print(f"Tamaño descifrado: {len(recovered_pdf)} bytes")
    print()

    if original_pdf == recovered_pdf:
        print("Cifrado y descifrado: OK (el PDF recuperado es idéntico al original)")
    else:
        print("Cifrado y descifrado: KO (el PDF recuperado no coincide con el original)")


if __name__ == "__main__":
    prueba_cifrado()
