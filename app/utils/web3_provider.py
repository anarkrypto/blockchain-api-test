from web3 import Web3

from app.constants import INFURA_API_KEY, VALID_NETWORKS, NetworkType


def getWeb3Provider(network: NetworkType) -> Web3:
    """
    Get a Web3 provider for the specified network.
    Args:
        network: The network to connect to.
    Returns:
        Web3: An instance of Web3 connected to the specified network.
    """
    if network not in VALID_NETWORKS:
        raise ValueError(f'Unsupported network: {network}')

    infura_url = f'https://{network}.infura.io/v3/{INFURA_API_KEY}'
    return Web3(Web3.HTTPProvider(infura_url))
