# Script de demostración de la consola para probar las funcionalidades desarrolladas en la aplicación.
# Este script permite al usuario interactuar con las funcionalidades de la aplicación a través de un menú.
# Se ha utilizado para probar todas las funcionalidades desarrolladas en la plataforma de gestión de certificados digitales. 
from scripts.upload_pinata_test import subir_certificado_pinata
from scripts.list_pinata_test import listar_certificados_pinata, descargar_certificado_pinata
from scripts.blockfrost_test import (
    consultar_ultimo_bloque,
    consultar_direccion_cardano,
    consultar_utxos,
    consultar_metadata_transaccion,
    verificar_certificado,
)
from scripts.crypto_test import prueba_cifrado
from scripts.permissions_organization_test import test_permissions
from scripts.jwt_test import test_jwt
from scripts.permissions_api_test import test_permissions_api
from scripts.students_api_test import test_students_api
from scripts.organizations_api_test import test_organizations_api
from scripts.administrators_api_test import test_administrators_api
from scripts.courses_api_test import test_courses_api
from scripts.enrollments_api_test import test_enrollments_api


def show_menu():
    print("=" * 60)
    print("Gestión de certificados Pinata/IPFS y Blockfrost/Cardano")
    print("=" * 60)
    print("1. Subir certificado (Pinata/IPFS)")
    print("2. Ver certificados subidos (Pinata/IPFS)")
    print("3. Descargar certificado por CID (Pinata/IPFS)")
    print("4. Consultar último bloque de Cardano (Blockfrost/Cardano)")
    print("5. Consultar información de la dirección de Cardano (Blockfrost/Cardano)")
    print("6. Consultar UTxOs de la dirección de Cardano (Blockfrost/Cardano)")
    print("7. Consultar metadatos (HASH y CID documento) de una transacción (Blockfrost/Cardano)")
    print("8. Verificar integridad de un certificado (Blockfrost/Cardano + Pinata/IPFS)")
    print("9. Probar cifrado y descifrado de un certificado (AES-256-GCM)")
    print("10. Probar permisos de acceso (PostgreSQL)")
    print("11. Probar autenticación JWT (API)")
    print("12. Probar API de permisos de acceso (grant/revoke/listar)")
    print("13. Probar API de gestión de alumnos (crear/listar/consultar)")
    print("14. Probar API de gestión de organizaciones (crear/listar/consultar)")
    print("15. Probar API de gestión de administradores (crear/listar/consultar)")
    print("16. Probar API de gestión de cursos (crear/consultar)")
    print("17. Probar API de gestión de matrículas (matricular/desmatricular)")
    print("18. Salir")


def main():
    while True:
        show_menu()
        opcion = input("Seleccione una opción: ").strip()
        print()

        if opcion == "1":
            subir_certificado_pinata()
        elif opcion == "2":
            listar_certificados_pinata()
        elif opcion == "3":
            descargar_certificado_pinata()
        elif opcion == "4":
            consultar_ultimo_bloque()
        elif opcion == "5":
            consultar_direccion_cardano()
        elif opcion == "6":
            consultar_utxos()
        elif opcion == "7":
            consultar_metadata_transaccion()
        elif opcion == "8":
            verificar_certificado()
        elif opcion == "9":
            prueba_cifrado()
        elif opcion == "10":
            test_permissions()
        elif opcion == "11":
            test_jwt()
        elif opcion == "12":
            test_permissions_api()
        elif opcion == "13":
            test_students_api()
        elif opcion == "14":
            test_organizations_api()
        elif opcion == "15":
            test_administrators_api()
        elif opcion == "16":
            test_courses_api()
        elif opcion == "17":
            test_enrollments_api()
        elif opcion == "18":
            break
        else:
            print("Opción no válida.")

        print()


if __name__ == "__main__":
    main()
