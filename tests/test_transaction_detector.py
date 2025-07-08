import pytest
from web3.exceptions import TransactionNotFound

from app.utils.transaction_detector import TransactionDetector

detector = TransactionDetector('mainnet')


def test_eth_only_transfer() -> None:
    tx_hash = (
        '0xe1f1d93ada575db0dbab0fa2e6f019e1baa55bf1a9ac728a658f7b8d202f4e9a'
    )
    from_address = '0x478a36710128daf0f0cf6a1fe5c953045dc7c8d7'
    to_address = '0x87a2c7e3895e975286b7d9fa34042fe70cd2fee3'
    block_number = 22861302
    eth_amount = 451792146704298000

    result = detector.detect_transaction(tx_hash)

    assert result.hash == tx_hash
    assert result.block_number == block_number
    assert len(result.eth_transfer) == 1
    assert len(result.transaction_type) == 1
    assert result.transaction_type[0] == 'ETH_TRANSFER'
    assert len(result.usdc_transfer) == 0
    assert result.from_address == from_address
    assert result.to_address == to_address
    assert result.eth_transfer[0].amount == eth_amount
    assert result.eth_transfer[0].from_address == from_address
    assert result.eth_transfer[0].to_address == to_address


def test_usdc_only_transfer() -> None:
    tx_hash = (
        '0xf2ba3f7b266c8c2780d807529f2b9a8f5e4703f8c5314aa2585ebb24a9538b39'
    )
    from_address = '0xec8bd58821b6dd99e917906ad16333bcd6e25c87'
    to_address = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    block_number = 22870084
    usdc_amount = 2353509986  # noqa: PLR2004

    result = detector.detect_transaction(tx_hash)

    assert result.hash == tx_hash
    assert result.block_number == block_number
    assert result.from_address == from_address
    assert result.to_address == to_address
    assert len(result.eth_transfer) == 0
    assert len(result.usdc_transfer) == 1
    assert result.usdc_transfer[0].token_address == to_address
    assert result.usdc_transfer[0].amount == usdc_amount
    assert result.from_address == from_address
    assert result.to_address == to_address
    assert len(result.transaction_type) == 1
    assert result.transaction_type[0] == 'USDC_TRANSFER'


def test_eth_and_usdc_transfer() -> None:
    tx_hash = (
        '0x4a929465fdf67c1e77c34efdc841ef4e19f0150d67eed8f646f3bd1ce89cac20'
    )
    result = detector.detect_transaction(tx_hash)
    assert len(result.eth_transfer) == 1
    assert len(result.usdc_transfer) == 3  # noqa: PLR2004
    assert len(result.transaction_type) == 2  # noqa: PLR2004
    assert result.transaction_type[0] == 'ETH_TRANSFER'
    assert result.transaction_type[1] == 'USDC_TRANSFER'


def test_other_transaction() -> None:
    tx_hash = (
        '0xdcb5253a69e1d9e7c5c3edc5a52478bc87a7cf875054590f823449a61483b98d'
    )
    result = detector.detect_transaction(tx_hash)
    assert len(result.eth_transfer) == 0
    assert len(result.usdc_transfer) == 0
    assert len(result.transaction_type) == 1
    assert result.transaction_type[0] == 'OTHER'


def test_not_found_transaction() -> None:
    tx_hash = (
        '0x0000000000000000000000000000000000000000000000000000000000000000'
    )
    with pytest.raises(TransactionNotFound):
        detector.detect_transaction(tx_hash)
