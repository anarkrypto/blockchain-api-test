import pytest
from web3.exceptions import TransactionNotFound

from app.utils.token_detector import TokenDetector

detector = TokenDetector('mainnet')


def test_eth_only_transfer() -> None:
    tx_hash = (
        '0xe1f1d93ada575db0dbab0fa2e6f019e1baa55bf1a9ac728a658f7b8d202f4e9a'
    )
    from_address = '0x478a36710128daf0f0cf6a1fe5c953045dc7c8d7'
    to_address = '0x87a2c7e3895e975286b7d9fa34042fe70cd2fee3'
    block_number = 22861302
    eth_amount = 451792146704298000

    result = detector.analyze_transaction(tx_hash)

    assert result.hash == tx_hash
    assert result.block_number == block_number
    assert len(result.transfers) == 1
    assert len(result.tokens) == 1
    assert result.tokens[0] == 'ETH'
    assert result.from_address == from_address
    assert result.to_address == to_address
    assert result.transfers[0].token == 'ETH'
    assert result.transfers[0].amount == eth_amount
    assert result.transfers[0].from_address == from_address
    assert result.transfers[0].to_address == to_address


def test_usdc_only_transfer() -> None:
    tx_hash = (
        '0xf2ba3f7b266c8c2780d807529f2b9a8f5e4703f8c5314aa2585ebb24a9538b39'
    )
    from_address = '0xec8bd58821b6dd99e917906ad16333bcd6e25c87'
    to_address = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    block_number = 22870084
    usdc_amount = 2353509986  # noqa: PLR2004

    result = detector.analyze_transaction(tx_hash)

    assert result.hash == tx_hash
    assert result.block_number == block_number
    assert result.from_address == from_address
    assert result.to_address == to_address
    assert len(result.transfers) == 1
    assert len(result.tokens) == 1
    assert result.tokens[0] == 'USDC'
    assert result.transfers[0].raw_contract.address == to_address
    assert result.transfers[0].amount == usdc_amount
    assert result.from_address == from_address
    assert result.to_address == to_address


def test_eth_and_usdc_transfer() -> None:
    tx_hash = (
        '0x4a929465fdf67c1e77c34efdc841ef4e19f0150d67eed8f646f3bd1ce89cac20'
    )
    result = detector.analyze_transaction(tx_hash)
    assert len(result.transfers) == 7  # noqa: PLR2004
    assert len(result.tokens) == 2  # noqa: PLR2004
    assert 'ETH' in result.tokens
    assert 'USDC' in result.tokens


def test_not_found_transaction() -> None:
    tx_hash = (
        '0x0000000000000000000000000000000000000000000000000000000000000000'
    )
    with pytest.raises(TransactionNotFound):
        detector.analyze_transaction(tx_hash)


def test_internal_transactions() -> None:
    tx_hash = (
        '0xc14f18ae1207497070b910160ff22866d6cad43a3e8354a76fcf3f7821056052'
    )
    result = detector.analyze_transaction(tx_hash)
    print(len(result.transfers))
    assert len(result.transfers) == 27  # noqa: PLR2004
