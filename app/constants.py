import os

from dotenv import load_dotenv

load_dotenv(override=True)
MNEMONIC = os.getenv('MNEMONIC')
