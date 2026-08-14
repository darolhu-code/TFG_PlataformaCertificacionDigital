
import os
from blockfrost import ApiUrls
from dotenv import load_dotenv
from pycardano import BlockFrostChainContext

load_dotenv()

BLOCKFROST_API_KEY = os.environ["BLOCKFROST_API_KEY"]


# Obtiene el contexto de la cadena de bloques de Cardano utilizando la API de Blockfrost
# Se utiliza para que pycardano pueda interactuar con la red de Cardano a través de la API de Blockfrost
# PyCardano es el encargado de crear las transacciones y firmarlas, mientras que Blockfrost es el encargado de enviarlas a Cardano
def get_chain_context() -> BlockFrostChainContext:
    return BlockFrostChainContext(
        BLOCKFROST_API_KEY,
        base_url=ApiUrls.preprod.value,
    )