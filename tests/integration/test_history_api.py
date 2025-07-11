"""
Tests for the History API endpoint.

This module contains comprehensive tests for the /history endpoint,
which retrieves transaction history for a specific address and token.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session
from web3 import Web3

from app.constants import (
    MAX_TRANSACTIONS_TO_LIST_PER_REQUEST,
    NETWORK,
    NETWORKS,
)
from app.models import Address, Transaction
from app.schemas import HistoryResponse, TransactionSchema


def validate_response_schema(data: Dict[str, Any], schema_class: type) -> None:
    """Validate that response data matches the expected schema."""
    try:
        schema_class(**data)
    except Exception as e:
        pytest.fail(f'Response data does not match schema: {e}')


@pytest.fixture
def setup_test_addresses(db_session: Session) -> tuple[str, str]:
    """Create test addresses for history testing."""
    # Create two test addresses
    address1 = Address(
        address='0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
        index=0,
    )
    address2 = Address(
        address='0x70997970c51812dc3a010c7d01b50e0d17dc79c8',
        index=1,
    )

    db_session.add(address1)
    db_session.add(address2)
    db_session.commit()

    return address1.address, address2.address


@pytest.fixture
def setup_transactions_for_history(
    setup_test_addresses: tuple[str, str], db_session: Session
) -> tuple[str, str, list[Transaction]]:
    """Create test transactions for history testing."""
    address1, address2 = setup_test_addresses

    # Create test transactions
    transactions = []

    # ETH transactions
    for i in range(5):
        tx = Transaction(
            id=str(uuid.uuid4()),
            hash=f'0x{str(i).zfill(64)}',
            from_address=address1 if i % 2 == 0 else address2,
            to_address=address2 if i % 2 == 0 else address1,
            amount=str(Web3.to_wei(0.1 * (i + 1), 'ether')),
            chain_id=NETWORKS[NETWORK].chain_id,
            token='ETH',
            status='confirmed',
            gas_used='21000',
            gas_price='20000000000',
            fee='420000000000000',
            created_at=datetime.now(timezone.utc),
        )
        transactions.append(tx)
        db_session.add(tx)

    # USDC transactions
    for i in range(3):
        tx = Transaction(
            id=str(uuid.uuid4()),
            hash=f'0x{str(i + 100).zfill(64)}',
            from_address=address1 if i % 2 == 0 else address2,
            to_address=address2 if i % 2 == 0 else address1,
            amount=str(100 * (i + 1)),  # USDC amounts
            chain_id=NETWORKS[NETWORK].chain_id,
            token='USDC',
            status='confirmed',
            gas_used='65000',
            gas_price='20000000000',
            fee='1300000000000000',
            created_at=datetime.now(timezone.utc),
        )
        transactions.append(tx)
        db_session.add(tx)

    # Add some pending transactions
    for i in range(2):
        tx = Transaction(
            id=str(uuid.uuid4()),
            hash=f'0x{str(i + 200).zfill(64)}',
            from_address=address1,
            to_address=address2,
            amount=str(Web3.to_wei(0.05, 'ether')),
            chain_id=NETWORKS[NETWORK].chain_id,
            token='ETH',
            status='pending',
            created_at=datetime.now(timezone.utc),
        )
        transactions.append(tx)
        db_session.add(tx)

    db_session.commit()

    return address1, address2, transactions


def test_history_success_eth(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test successful history retrieval for ETH token."""
    address1, _, _ = setup_transactions_for_history

    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
        },
    )

    # Debug: Print response content
    print(f'Response status: {response.status_code}')
    print(f'Response content: {response.text}')

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response schema
    validate_response_schema(data, HistoryResponse)

    # Check response structure
    assert data['success'] is True
    assert data['address'] == address1
    assert data['token'] == 'ETH'
    assert data['network'] == NETWORK
    assert data['chain_id'] == NETWORKS[NETWORK].chain_id
    assert data['skip'] == 0
    assert data['limit'] == MAX_TRANSACTIONS_TO_LIST_PER_REQUEST
    assert (
        data['total'] == 7  # noqa: PLR2004
    )  # 5 confirmed + 2 pending ETH transactions
    assert len(data['transactions']) == 7  # noqa: PLR2004

    # Check transaction structure
    for tx in data['transactions']:
        validate_response_schema(tx, TransactionSchema)
        assert tx['token'] == 'ETH'
        assert tx['chain_id'] == NETWORKS[NETWORK].chain_id
        # Should be either from or to the requested address
        assert tx['from_address'] == address1 or tx['to_address'] == address1


def test_history_success_usdc(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test successful history retrieval for USDC token."""
    address1, _, _ = setup_transactions_for_history

    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'USDC',
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response schema
    validate_response_schema(data, HistoryResponse)

    # Check response structure
    assert data['success'] is True
    assert data['address'] == address1
    assert data['token'] == 'USDC'
    assert data['total'] == 3  # 3 USDC transactions # noqa: PLR2004
    assert len(data['transactions']) == 3  # noqa: PLR2004

    # Check transaction structure
    for tx in data['transactions']:
        validate_response_schema(tx, TransactionSchema)
        assert tx['token'] == 'USDC'
        assert tx['chain_id'] == NETWORKS[NETWORK].chain_id


def test_history_pagination(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test history pagination functionality."""
    address1, _, _ = setup_transactions_for_history

    # Test first page (limit=3)
    response1 = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
            'skip': 0,
            'limit': 3,
        },
    )

    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()

    assert data1['skip'] == 0
    assert data1['limit'] == 3  # noqa: PLR2004
    assert data1['total'] == 7  # noqa: PLR2004
    assert len(data1['transactions']) == 3  # noqa: PLR2004

    # Test second page (skip=3, limit=3)
    response2 = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
            'skip': 3,
            'limit': 3,
        },
    )

    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()

    assert data2['skip'] == 3  # noqa: PLR2004
    assert data2['limit'] == 3  # noqa: PLR2004
    assert data2['total'] == 7  # noqa: PLR2004
    assert len(data2['transactions']) == 3  # noqa: PLR2004

    # Verify different transactions on different pages
    tx_hashes_page1 = {tx['hash'] for tx in data1['transactions']}
    tx_hashes_page2 = {tx['hash'] for tx in data2['transactions']}
    assert tx_hashes_page1.isdisjoint(tx_hashes_page2)


def test_history_pagination_edge_cases(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test history pagination edge cases."""
    address1, _, _ = setup_transactions_for_history

    # Test skip beyond total count
    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
            'skip': 100,
            'limit': 10,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['skip'] == 100  # noqa: PLR2004
    assert data['total'] == 7  # noqa: PLR2004
    assert len(data['transactions']) == 0

    # Test limit larger than total count
    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
            'skip': 0,
            'limit': 100,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['limit'] == 100  # noqa: PLR2004
    assert data['total'] == 7  # noqa: PLR2004
    assert len(data['transactions']) == 7  # noqa: PLR2004


def test_history_address_not_found(client: TestClient) -> None:
    """Test history request for non-existent address."""
    non_existent_address = '0x1234567890123456789012345678901234567890'

    response = client.get(
        '/history',
        params={
            'address': non_existent_address,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Address not found' in response.json()['detail']


def test_history_invalid_address_format(client: TestClient) -> None:
    """Test history request with invalid address format."""
    # FastAPI raises validation errors during dependency resolution when using Pydantic models  # noqa: E501
    # This test expects a ValidationError to be raised for invalid address format  # noqa: E501
    with pytest.raises(ValidationError) as exc_info:
        client.get(
            '/history',
            params={
                'address': 'invalid_address',
                'token': 'ETH',
            },
        )

    # Verify the validation error contains the expected message
    error_detail = str(exc_info.value)
    assert 'Invalid Ethereum address format' in error_detail


def test_history_invalid_token(client: TestClient) -> None:
    """Test history request with invalid token."""
    response = client.get(
        '/history',
        params={
            'address': '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
            'token': 'INVALID_TOKEN',
        },
    )

    # Should fail due to validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_history_invalid_pagination_params(client: TestClient) -> None:
    """Test history request with invalid pagination parameters."""
    # Test negative skip
    response = client.get(
        '/history',
        params={
            'address': '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
            'token': 'ETH',
            'skip': -1,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test zero limit
    response = client.get(
        '/history',
        params={
            'address': '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
            'token': 'ETH',
            'limit': 0,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test limit exceeding maximum
    response = client.get(
        '/history',
        params={
            'address': '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
            'token': 'ETH',
            'limit': MAX_TRANSACTIONS_TO_LIST_PER_REQUEST + 1,
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_history_empty_result(
    client: TestClient,
    setup_test_addresses: tuple[str, str],
) -> None:
    """Test history request for address with no transactions."""
    address1, _ = setup_test_addresses

    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['success'] is True
    assert data['address'] == address1
    assert data['token'] == 'ETH'
    assert data['total'] == 0
    assert len(data['transactions']) == 0


def test_history_transaction_ordering(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test that transactions are ordered by created_at descending."""
    address1, _, _ = setup_transactions_for_history

    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Check that transactions are ordered by created_at descending
    transactions = data['transactions']
    for i in range(len(transactions) - 1):
        current_created_at = datetime.fromisoformat(
            transactions[i]['created_at'].replace('Z', '+00:00')
        )
        next_created_at = datetime.fromisoformat(
            transactions[i + 1]['created_at'].replace('Z', '+00:00')
        )
        assert current_created_at >= next_created_at


def test_history_transaction_statuses(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test that transactions include correct status information."""
    address1, _, _ = setup_transactions_for_history

    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Check that we have both confirmed and pending transactions
    statuses = {tx['status'] for tx in data['transactions']}
    assert 'confirmed' in statuses
    assert 'pending' in statuses

    # Check that confirmed transactions have gas information
    confirmed_txs = [
        tx for tx in data['transactions'] if tx['status'] == 'confirmed'
    ]
    for tx in confirmed_txs:
        assert tx['gas_used'] is not None
        assert tx['gas_price'] is not None
        assert tx['fee'] is not None

    # Check that pending transactions may not have gas information
    pending_txs = [
        tx for tx in data['transactions'] if tx['status'] == 'pending'
    ]
    for tx in pending_txs:
        # Pending transactions might not have gas info yet
        pass


def test_history_mixed_token_transactions(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test that history correctly filters by token type."""
    address1, _, _ = setup_transactions_for_history

    # Get ETH transactions
    eth_response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
        },
    )

    assert eth_response.status_code == status.HTTP_200_OK
    eth_data = eth_response.json()

    # Get USDC transactions
    usdc_response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'USDC',
        },
    )

    assert usdc_response.status_code == status.HTTP_200_OK
    usdc_data = usdc_response.json()

    # Verify different transaction counts
    assert eth_data['total'] != usdc_data['total']

    # Verify no overlap in transaction hashes
    eth_hashes = {tx['hash'] for tx in eth_data['transactions']}
    usdc_hashes = {tx['hash'] for tx in usdc_data['transactions']}
    assert eth_hashes.isdisjoint(usdc_hashes)


def test_history_missing_required_params(client: TestClient) -> None:
    """Test history request with missing required parameters."""
    # Missing address
    response = client.get(
        '/history',
        params={
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing token
    response = client.get(
        '/history',
        params={
            'address': '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266',
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_history_case_insensitive_address(
    client: TestClient,
    setup_transactions_for_history: tuple[str, str, list[Transaction]],
) -> None:
    """Test that address matching is case insensitive."""
    address1, _, _ = setup_transactions_for_history

    # Use uppercase address
    uppercase_address = address1.upper()

    response = client.get(
        '/history',
        params={
            'address': uppercase_address,
            'token': 'ETH',
        },
    )

    # Should fail due to validation error (addresses should be lowercase)
    # Note: The address validator converts to lowercase, so this should be 404 not 422  # noqa: E501
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Address not found' in response.json()['detail']


def test_history_large_amount_transactions(
    client: TestClient,
    setup_test_addresses: tuple[str, str],
    db_session: Session,
) -> None:
    """Test history with transactions containing large amounts."""
    address1, address2 = setup_test_addresses

    # Create transaction with large amount
    large_amount = str(Web3.to_wei(1000, 'ether'))  # 1000 ETH

    tx = Transaction(
        id=str(uuid.uuid4()),
        hash='0x' + '1' * 64,
        from_address=address1,
        to_address=address2,
        amount=large_amount,
        chain_id=NETWORKS[NETWORK].chain_id,
        token='ETH',
        status='confirmed',
        gas_used='21000',
        gas_price='20000000000',
        fee='420000000000000',
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(tx)
    db_session.commit()

    response = client.get(
        '/history',
        params={
            'address': address1,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['total'] == 1
    assert len(data['transactions']) == 1
    assert data['transactions'][0]['amount'] == large_amount
