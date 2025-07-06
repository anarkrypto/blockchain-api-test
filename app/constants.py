import os

from dotenv import load_dotenv

load_dotenv(override=True)
MNEMONIC = os.getenv('MNEMONIC')
MAX_ADDRESSES_TO_GENERATE_PER_REQUEST = 1000
MAX_ADDRESSES_TO_LIST_PER_REQUEST = 1000
