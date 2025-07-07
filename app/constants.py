import os

from dotenv import load_dotenv

load_dotenv(override=True)
MNEMONIC = os.getenv('MNEMONIC')
MAX_ADDRESSES_TO_GENERATE_PER_REQUEST = 100
MAX_ADDRESSES_TO_LIST_PER_REQUEST = 100
INFURA_API_KEY = os.getenv('INFURA_API_KEY')
