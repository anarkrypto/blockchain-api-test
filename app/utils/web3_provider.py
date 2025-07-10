from web3 import Web3

from app.constants import ALCHEMY_API_KEY, VALID_NETWORKS, NetworkType


def get_web3_provider(network: NetworkType) -> Web3:
    """
    Get a Web3 provider for the specified network.
    Args:
        network: The network to connect to.
    Returns:
        Web3: An instance of Web3 connected to the specified network.
    """
    if network not in VALID_NETWORKS:
        raise ValueError(f'Unsupported network: {network}')

    alchemy_url = f'https://eth-{network}.g.alchemy.com/v2/{ALCHEMY_API_KEY}'
    return Web3(Web3.HTTPProvider(alchemy_url))
