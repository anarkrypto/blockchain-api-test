from typing import Callable, Generator, List

import pytest
from eth_tester import EthereumTester
from eth_tester.backends.pyevm.main import PyEVMBackend
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from app.constants import NetworkType
from app.database import get_db
from app.main import app
from app.models import Base
from tests.tests_utils.test_token_detector import TestTokenDetector


@pytest.fixture(autouse=True)
def patch_mnemonic() -> Generator[None, None, None]:
    """Patch the MNEMONIC constant for all tests in this module."""
    test_mnemonic = 'clinic flight consider display dash rubber subject language glare duck replace snack'  # noqa: E501

    with pytest.MonkeyPatch().context() as m:
        # Patch the MNEMONIC constant in app.constants
        m.setattr('app.constants.MNEMONIC', test_mnemonic)
        yield


@pytest.fixture
def eth_tester() -> EthereumTester:
    """Create a fresh Ethereum tester instance for each test."""
    return EthereumTester(PyEVMBackend())


@pytest.fixture
def w3(eth_tester: EthereumTester) -> Web3:
    """Create a Web3 instance connected to eth-tester."""
    return Web3(EthereumTesterProvider(eth_tester))


@pytest.fixture
def funded_accounts(w3: Web3) -> List[str]:
    """Get list of funded accounts from eth-tester."""
    return [account for account in w3.eth.accounts]


@pytest.fixture
def funded_account(w3: Web3, funded_accounts: List[str]) -> str:
    """Get the first funded account (has 1000 ETH by default)."""
    return funded_accounts[0]


@pytest.fixture
def create_test_detector(
    w3: Web3,
) -> Callable[[NetworkType], TestTokenDetector]:
    """Create a TestTokenDetector factory function."""

    def _create_test_detector(network: NetworkType) -> TestTokenDetector:
        return TestTokenDetector(w3)

    return _create_test_detector


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    # Create a fresh in-memory engine for each test
    # with StaticPool to maintain a single connection
    engine = create_engine(
        'sqlite:///:memory:',
        future=True,
        connect_args={
            'check_same_thread': False,
        },
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables directly from the SQLAlchemy models
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


# Inject DB session into FastAPI
@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
