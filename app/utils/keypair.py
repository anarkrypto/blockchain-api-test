from bip_utils import (
    Bip39MnemonicValidator,
    Bip39SeedGenerator,
    Bip44,
    Bip44Changes,
    Bip44Coins,
)
from eth_account import Account

from app.constants import MNEMONIC
from app.schemas import KeyPair


def generate_keypair(index: int) -> KeyPair:
    # Validate the mnemonic
    assert Bip39MnemonicValidator().IsValid(MNEMONIC), 'Invalid mnemonic'

    # Generate seed from mnemonic
    seed_bytes = Bip39SeedGenerator(MNEMONIC).Generate()

    # Derive Ethereum account using BIP44 path: m/44'/60'/0'/0/0
    bip44_wallet = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
    account = (
        bip44_wallet.Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
    )

    private_key_hex = account.PrivateKey().Raw().ToHex()
    eth_account = Account.from_key(private_key_hex)

    return KeyPair(
        address=eth_account.address,
        private_key=private_key_hex,
    )
