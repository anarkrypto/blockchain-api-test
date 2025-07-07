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
