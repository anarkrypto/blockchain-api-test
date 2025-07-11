import uuid
from threading import Event
from typing import Any, Dict, List

import pytest
from eth_utils.address import to_checksum_address
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3

from app.constants import NETWORK, NETWORKS, NetworkType
from app.models import Balance, ProcessedTransaction, Transaction
from app.schemas import WithdrawResponse
from app.utils.keypair import generate_keypair
from tests.conftest import Web3Tester


def validate_response_schema(data: Dict[str, Any], schema_class: type) -> None:
    """Validate that the response data matches the expected schema."""
    schema_class(**data)


def create_mock_wallet_and_processor(
    w3: Web3Tester, from_address: str, address_index: int = 0
) -> tuple[type, type]:
    """Create mock Wallet and ReceiptProcessor classes for testing."""
    keypair = generate_keypair(address_index)
    private_key = keypair.private_key
    checksum_from_address = to_checksum_address(from_address)

    class MockWallet:
        def __init__(self, network: NetworkType, account_index: int) -> None:
            self.w3 = w3
            self.network = NETWORKS[network]
            self.from_address = checksum_from_address
            self.private_key = private_key

        def transfer(
            self, token: str, to_address: str, amount: int
        ) -> Transaction:
            to_address = to_checksum_address(to_address)
            nonce = self.w3.eth.get_transaction_count(self.from_address)
            tx = {
                'to': to_address,
                'value': amount,
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
                'chainId': self.network.chain_id,
            }
            signed_tx = self.w3.eth.account.sign_transaction(
                tx, self.private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(
                signed_tx.raw_transaction
            )
            self.w3.provider.ethereum_tester.mine_blocks(1)
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            gas_price = int(str(tx['gasPrice']))
            return Transaction(
                id=str(uuid.uuid4()),
                hash=tx_hash.hex(),
                from_address=self.from_address,
                to_address=to_address,
                amount=str(amount),
                chain_id=self.network.chain_id,
                token=token,
                status='pending',
                gas_used=str(receipt['gasUsed']),
                gas_price=str(gas_price),
                fee=str(receipt['gasUsed'] * gas_price),
            )

    class MockReceiptProcessor:
        def __init__(self, network: NetworkType):
            self.w3 = w3  # Use eth-tester Web3 instance
            self.pending_transactions: List[Transaction] = []
            self.started = False
            self._stop_event = Event()

        def add_pending_transaction(self, transaction: Transaction) -> None:
            self.pending_transactions.append(transaction)

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.started = False

    return MockWallet, MockReceiptProcessor


@pytest.fixture
def generate_test_addresses(client: TestClient) -> tuple[str, str]:
    """Generate two test addresses for withdrawal testing."""
    # Addresses generated with the test mnemonic
    test_address_0 = '0xf39b278078f5488ca53b57eea65a9186d17e06e3'
    test_address_1 = '0x4bb67806f3d073d5d57c2015401af5934db5a16c'

    # Generate 2 addresses
    response = client.post('/addresses', json={'quantity': 2})
    assert response.status_code == status.HTTP_200_OK

    # Get the generated addresses
    list_response = client.get('/addresses?limit=2')
    assert list_response.status_code == status.HTTP_200_OK
    addresses = list_response.json()['addresses']

    assert len(addresses) == 2  # noqa: PLR2004
    assert addresses[0] == test_address_0
    assert addresses[1] == test_address_1
    return addresses[0], addresses[1]


@pytest.fixture
def setup_balance_with_funding(
    generate_test_addresses: tuple[str, str],
    db_session: Session,
    w3: Web3Tester,
) -> tuple[str, str, int]:
    """Setup a test address with ETH balance for withdrawal testing."""
    from_address, to_address = generate_test_addresses
    db_from_address = from_address.lower()
    checksum_from_address = to_checksum_address(from_address)
    # Fund the from_address with some ETH from eth-tester's default account
    amount_wei = Web3.to_wei(0.2, 'ether')
    default_account = w3.eth.accounts[0]
    tx = {
        'to': checksum_from_address,
        'value': amount_wei,
        'gas': 21000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(default_account),
        'chainId': w3.eth.chain_id,
    }
    signed_tx = w3.eth.account.sign_transaction(
        tx,
        '0x0000000000000000000000000000000000000000000000000000000000000001',  # eth-tester default privkey  # noqa: E501
    )
    w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.provider.ethereum_tester.mine_blocks(1)
    # Create a balance record in the database
    balance = Balance(
        address=db_from_address,
        balance=str(amount_wei),
        token='ETH',
        chain_id=NETWORKS[NETWORK].chain_id,
    )
    db_session.add(balance)
    db_session.commit()
    return db_from_address, to_address, amount_wei


def test_withdraw_eth_success(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
    w3: Web3Tester,
) -> None:
    """Test successful ETH withdrawal between addresses."""
    from_address, to_address, initial_balance = setup_balance_with_funding

    # Patch the Wallet and ReceiptProcessor classes to use eth-tester
    with pytest.MonkeyPatch().context() as m:
        MockWallet, MockReceiptProcessor = create_mock_wallet_and_processor(
            w3, from_address, 0
        )

        # Replace the Wallet class with our mock
        m.setattr('app.main.Wallet', MockWallet)
        # Replace the ReceiptProcessor with our mock
        m.setattr('app.main.receipt_processor', MockReceiptProcessor(NETWORK))

        # Withdraw amount (less than initial balance)
        withdraw_amount = Web3.to_wei(0.05, 'ether')

        response = client.post(
            '/withdraw',
            json={
                'from_address': from_address,
                'to_address': to_address,
                'amount': withdraw_amount,
                'token': 'ETH',
            },
        )

        if response.status_code != status.HTTP_200_OK:
            print(f'Response status: {response.status_code}')
            print(f'Response content: {response.json()}')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate response schema
        validate_response_schema(data, WithdrawResponse)

        # Verify response data
        assert data['success'] is True
        assert data['from_address'] == from_address
        assert data['to_address'] == to_address
        assert data['amount'] == withdraw_amount
        assert data['token'] == 'ETH'
        assert data['network'] == NETWORK
        assert data['chain_id'] == NETWORKS[NETWORK].chain_id
        assert data['status'] == 'pending'
        assert data['hash'] is not None
        assert data['gas_used'] is not None
        assert data['gas_price'] is not None
        assert data['fee'] is not None


def test_withdraw_usdc_success(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
    db_session: Session,
    w3: Web3Tester,
) -> None:
    """Test successful USDC withdrawal between addresses."""
    from_address, to_address, _ = setup_balance_with_funding

    # Setup USDC balance
    usdc_amount = 1000000  # 1 USDC (6 decimals)
    usdc_balance = Balance(
        address=from_address,
        balance=str(usdc_amount),
        token='USDC',
        chain_id=NETWORKS[NETWORK].chain_id,
    )
    db_session.add(usdc_balance)
    db_session.commit()

    # Patch the Wallet and ReceiptProcessor classes to use eth-tester
    with pytest.MonkeyPatch().context() as m:
        MockWallet, MockReceiptProcessor = create_mock_wallet_and_processor(
            w3, from_address, 0
        )

        # Replace the Wallet class with our mock
        m.setattr('app.main.Wallet', MockWallet)
        # Replace the ReceiptProcessor with our mock
        m.setattr('app.main.receipt_processor', MockReceiptProcessor(NETWORK))

        # Withdraw USDC
        withdraw_amount = 500000  # 0.5 USDC

        response = client.post(
            '/withdraw',
            json={
                'from_address': from_address,
                'to_address': to_address,
                'amount': withdraw_amount,
                'token': 'USDC',
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate response schema
        validate_response_schema(data, WithdrawResponse)

        # Verify response data
        assert data['success'] is True
        assert data['from_address'] == from_address
        assert data['to_address'] == to_address
        assert data['amount'] == withdraw_amount
        assert data['token'] == 'USDC'
        assert data['network'] == NETWORK
        assert data['chain_id'] == NETWORKS[NETWORK].chain_id
        assert data['status'] == 'pending'
        assert data['hash'] is not None
        assert data['gas_used'] is not None
        assert data['gas_price'] is not None
        assert data['fee'] is not None


def test_withdraw_address_not_found(client: TestClient) -> None:
    """Test withdrawal with non-existent address."""
    non_existent_address = '0x1234567890123456789012345678901234567890'

    response = client.post(
        '/withdraw',
        json={
            'from_address': non_existent_address,
            'to_address': '0x4bb67806f3d073d5d57c2015401af5934db5a16c',
            'amount': Web3.to_wei(0.01, 'ether'),
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert 'Address not found' in response.json()['detail']


def test_withdraw_insufficient_funds(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
) -> None:
    """Test withdrawal with insufficient funds."""
    from_address, to_address, initial_balance = setup_balance_with_funding

    # Try to withdraw more than available balance
    excessive_amount = initial_balance + Web3.to_wei(0.1, 'ether')

    response = client.post(
        '/withdraw',
        json={
            'from_address': from_address,
            'to_address': to_address,
            'amount': excessive_amount,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Insufficient funds' in response.json()['detail']


def test_withdraw_invalid_amount(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
) -> None:
    """Test withdrawal with invalid amount (zero or negative)."""
    from_address, to_address, _ = setup_balance_with_funding

    # Test with zero amount
    response = client.post(
        '/withdraw',
        json={
            'from_address': from_address,
            'to_address': to_address,
            'amount': 0,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Invalid amount' in response.json()['detail']

    # Test with negative amount
    response = client.post(
        '/withdraw',
        json={
            'from_address': from_address,
            'to_address': to_address,
            'amount': -1000,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Invalid amount' in response.json()['detail']


def test_withdraw_no_balance_record(
    client: TestClient,
    generate_test_addresses: tuple[str, str],
) -> None:
    """Test withdrawal when address exists but has no balance record."""
    from_address, to_address = generate_test_addresses

    response = client.post(
        '/withdraw',
        json={
            'from_address': from_address,
            'to_address': to_address,
            'amount': Web3.to_wei(0.01, 'ether'),
            'token': 'ETH',
        },
    )

    # Should fail due to insufficient funds (no balance record = 0 balance)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Insufficient funds' in response.json()['detail']


def test_withdraw_transaction_persistence(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
    db_session: Session,
    w3: Web3Tester,
) -> None:
    """Test that withdrawal transaction is properly persisted in database."""
    from_address, to_address, initial_balance = setup_balance_with_funding
    checksum_from_address = to_checksum_address(from_address)
    # Patch the Wallet and ReceiptProcessor classes to use eth-tester
    with pytest.MonkeyPatch().context() as m:
        MockWallet, MockReceiptProcessor = create_mock_wallet_and_processor(
            w3, checksum_from_address, 0
        )
        m.setattr('app.main.Wallet', MockWallet)
        m.setattr('app.main.receipt_processor', MockReceiptProcessor(NETWORK))
        withdraw_amount = Web3.to_wei(0.05, 'ether')
        response = client.post(
            '/withdraw',
            json={
                'from_address': from_address,  # lowercased for API
                'to_address': to_address,
                'amount': withdraw_amount,
                'token': 'ETH',
            },
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    tx_hash = data['hash']
    # Verify transaction is stored in database
    transaction = db_session.query(Transaction).filter_by(hash=tx_hash).first()
    assert transaction is not None
    assert transaction.from_address is not None
    assert transaction.to_address is not None
    assert transaction.from_address.lower() == from_address.lower()
    assert transaction.to_address.lower() == to_address.lower()
    assert transaction.amount == str(withdraw_amount)
    assert transaction.token == 'ETH'
    assert transaction.chain_id == NETWORKS[NETWORK].chain_id
    assert transaction.status == 'pending'
    assert transaction.gas_used is not None
    assert transaction.gas_price is not None
    assert transaction.fee is not None
    # Verify processed transaction record is created
    processed_tx = (
        db_session.query(ProcessedTransaction).filter_by(hash=tx_hash).first()
    )
    assert processed_tx is not None
    assert processed_tx.chain_id == NETWORKS[NETWORK].chain_id


def test_withdraw_multiple_transactions(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
    w3: Web3Tester,
) -> None:
    """Test multiple withdrawals from the same address."""
    from_address, to_address, initial_balance = setup_balance_with_funding

    # Patch the Wallet and ReceiptProcessor classes to use eth-tester
    with pytest.MonkeyPatch().context() as m:
        MockWallet, MockReceiptProcessor = create_mock_wallet_and_processor(
            w3, from_address, 0
        )
        m.setattr('app.main.Wallet', MockWallet)
        m.setattr('app.main.receipt_processor', MockReceiptProcessor(NETWORK))

        # First withdrawal
        withdraw_amount_1 = Web3.to_wei(0.02, 'ether')
        response1 = client.post(
            '/withdraw',
            json={
                'from_address': from_address,
                'to_address': to_address,
                'amount': withdraw_amount_1,
                'token': 'ETH',
            },
        )

        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1['success'] is True
        assert data1['amount'] == withdraw_amount_1

        # Second withdrawal
        withdraw_amount_2 = Web3.to_wei(0.03, 'ether')
        response2 = client.post(
            '/withdraw',
            json={
                'from_address': from_address,
                'to_address': to_address,
                'amount': withdraw_amount_2,
                'token': 'ETH',
            },
        )

        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2['success'] is True
        assert data2['amount'] == withdraw_amount_2

        # Verify different transaction hashes
        assert data1['hash'] != data2['hash']


def test_withdraw_to_same_address(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
    w3: Web3,
) -> None:
    """Test withdrawal to the same address is not allowed."""
    from_address, _, initial_balance = setup_balance_with_funding

    withdraw_amount = Web3.to_wei(0.01, 'ether')

    response = client.post(
        '/withdraw',
        json={
            'from_address': from_address,
            'to_address': from_address,  # Same address
            'amount': withdraw_amount,
            'token': 'ETH',
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        'From and to addresses cannot be the same' in response.json()['detail']
    )


def test_withdraw_invalid_token(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
) -> None:
    """Test withdrawal with invalid token type."""
    from_address, to_address, _ = setup_balance_with_funding

    response = client.post(
        '/withdraw',
        json={
            'from_address': from_address,
            'to_address': to_address,
            'amount': Web3.to_wei(0.01, 'ether'),
            'token': 'INVALID_TOKEN',  # Invalid token
        },
    )

    # Should fail due to validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_withdraw_missing_required_fields(client: TestClient) -> None:
    """Test withdrawal with missing required fields."""
    # Missing from_address
    response = client.post(
        '/withdraw',
        json={
            'to_address': '0x4bb67806f3d073d5d57c2015401af5934db5a16c',
            'amount': Web3.to_wei(0.01, 'ether'),
            'token': 'ETH',
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing to_address
    response = client.post(
        '/withdraw',
        json={
            'from_address': '0xf39b278078f5488ca53b57eea65a9186d17e06e3',
            'amount': Web3.to_wei(0.01, 'ether'),
            'token': 'ETH',
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing amount
    response = client.post(
        '/withdraw',
        json={
            'from_address': '0xf39b278078f5488ca53b57eea65a9186d17e06e3',
            'to_address': '0x4bb67806f3d073d5d57c2015401af5934db5a16c',
            'token': 'ETH',
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing token
    response = client.post(
        '/withdraw',
        json={
            'from_address': '0xf39b278078f5488ca53b57eea65a9186d17e06e3',
            'to_address': '0x4bb67806f3d073d5d57c2015401af5934db5a16c',
            'amount': Web3.to_wei(0.01, 'ether'),
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_withdraw_invalid_address_format(client: TestClient) -> None:
    """Test withdrawal with invalid address format."""
    response = client.post(
        '/withdraw',
        json={
            'from_address': 'invalid_address',
            'to_address': '0x4bb67806f3d073d5d57c2015401af5934db5a16c',
            'amount': Web3.to_wei(0.01, 'ether'),
            'token': 'ETH',
        },
    )

    # Should fail due to validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_withdraw_balance_consistency(
    client: TestClient,
    setup_balance_with_funding: tuple[str, str, int],
    db_session: Session,
    w3: Web3Tester,
) -> None:
    """Test that withdrawal properly handles balance consistency."""
    from_address, to_address, initial_balance = setup_balance_with_funding

    # Check initial balance
    initial_balance_record = (
        db_session.query(Balance)
        .filter_by(
            address=from_address,
            token='ETH',
            chain_id=NETWORKS[NETWORK].chain_id,
        )
        .first()
    )
    assert initial_balance_record is not None
    assert int(initial_balance_record.balance) == initial_balance

    # Patch the Wallet and ReceiptProcessor classes to use eth-tester
    with pytest.MonkeyPatch().context() as m:
        MockWallet, MockReceiptProcessor = create_mock_wallet_and_processor(
            w3, from_address, 0
        )
        m.setattr('app.main.Wallet', MockWallet)
        m.setattr('app.main.receipt_processor', MockReceiptProcessor(NETWORK))

        # Perform withdrawal
        withdraw_amount = Web3.to_wei(0.05, 'ether')
        response = client.post(
            '/withdraw',
            json={
                'from_address': from_address,
                'to_address': to_address,
                'amount': withdraw_amount,
                'token': 'ETH',
            },
        )

    assert response.status_code == status.HTTP_200_OK

    # Verify transaction was created
    data = response.json()
    transaction = (
        db_session.query(Transaction).filter_by(hash=data['hash']).first()
    )
    assert transaction is not None
    assert transaction.status == 'pending'

    # Note: In a real scenario, the balance would be updated by the receipt processor  # noqa: E501
    # after the transaction is confirmed. For testing purposes, we verify the transaction  # noqa: E501
    # was created with pending status.


def test_history_invalid_address_format(client: TestClient) -> None:
    """Test history request with invalid address format."""
    response = client.get(
        '/history',
        params={
            'address': 'invalid_address',
            'token': 'ETH',
        },
    )

    # Should fail due to validation error
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
