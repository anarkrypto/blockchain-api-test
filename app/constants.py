import os

from dotenv import load_dotenv
from eth_typing import ChainId
from eth_utils.network import Network

load_dotenv(override=True)
MNEMONIC = os.getenv('MNEMONIC')
MAX_ADDRESSES_TO_GENERATE_PER_REQUEST = 100
MAX_ADDRESSES_TO_LIST_PER_REQUEST = 100
INFURA_API_KEY = os.getenv('INFURA_API_KEY')

NETWORK = os.getenv('NETWORK', 'sepolia')
assert NETWORK in {'mainnet', 'sepolia'}, (
    f'Invalid NETWORK value: {NETWORK}. Must be "mainnet" or "sepolia".'
)

NETWORKS = {
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
