from bip_utils import Bip39MnemonicValidator
from eth_account import Account

from app.constants import MNEMONIC
from app.schemas import KeyPair
from app.utils.keypair import generate_keypair


def test_mnemonic_is_valid() -> None:
    assert Bip39MnemonicValidator().IsValid(MNEMONIC) is True


def test_generate_keypair_returns_keypair_instance() -> None:
    keypair = generate_keypair(0)
    assert isinstance(keypair, KeyPair)
    assert isinstance(keypair.address, str)
    assert isinstance(keypair.private_key, str)


def test_generate_keypair_derives_different_addresses() -> None:
    kp1 = generate_keypair(0)
    kp2 = generate_keypair(1)
    assert kp1.address != kp2.address
    assert kp1.private_key != kp2.private_key


def test_generate_keypair_returns_valid_eth_account() -> None:
    keypair = generate_keypair(0)
    acct = Account.from_key(keypair.private_key)
    assert acct.address == keypair.address
