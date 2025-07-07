import os
from typing import Dict, Literal, cast, get_args

from dotenv import load_dotenv
from eth_typing import ChainId
from eth_utils.network import Network

load_dotenv(override=True)
MNEMONIC = cast(str, os.getenv('MNEMONIC'))
assert MNEMONIC, 'MNEMONIC environment variable must be set.'

INFURA_API_KEY = cast(str, os.getenv('INFURA_API_KEY'))
assert INFURA_API_KEY, 'INFURA_API_KEY environment variable must be set.'

NetworkType = Literal['mainnet', 'sepolia']

VALID_NETWORKS = list(get_args(NetworkType))

NETWORK = cast(NetworkType, os.getenv('NETWORK', 'sepolia'))
assert NETWORK in VALID_NETWORKS, (
    f'Invalid NETWORK value: {NETWORK}. Must be one of: {VALID_NETWORKS}.'
)

NETWORKS: Dict[NetworkType, Network] = {
    'mainnet': Network(
        chain_id=1, name='mainnet', shortName='eth', symbol=ChainId(1)
    ),
    'sepolia': Network(
        chain_id=11155111,
        name='sepolia',
        shortName='sep',
        symbol=ChainId(11155111),
    ),
}

# Source: https://developers.circle.com/stablecoins/usdc-contract-addresses
USDC_CONTRACTS: Dict[NetworkType, str] = {
    'mainnet': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
    'sepolia': '0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238',
}


MAX_ADDRESSES_TO_GENERATE_PER_REQUEST = 100
MAX_ADDRESSES_TO_LIST_PER_REQUEST = 100
