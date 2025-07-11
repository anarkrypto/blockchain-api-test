"""
Test wallet implementation using eth-tester for local blockchain testing.
"""

import uuid
from typing import Optional

from eth_utils.address import to_checksum_address

from app.constants import NETWORKS
from app.models import Transaction
from tests.conftest import Web3Tester


class TestWallet:
    """Wallet implementation for testing using eth-tester local blockchain."""

    def __init__(self, w3: Web3Tester, from_address: str, private_key: str):
        self.w3 = w3
        self.from_address = to_checksum_address(from_address)
        self.private_key = private_key
        self.network = NETWORKS[
            'sepolia'
        ]  # Use sepolia config for consistency

    @classmethod
    def from_account_index(
        cls, w3: Web3Tester, account_index: int
    ) -> 'TestWallet':
        """Create wallet from account index using eth-tester accounts."""
        accounts = w3.eth.accounts
        if account_index >= len(accounts):
            raise ValueError(f'Account index {account_index} not available')

        # For eth-tester, we can get the private key directly
        # The first account has a known private key
        if account_index == 0:
            private_key = '0x0000000000000000000000000000000000000000000000000000000000000001'  # noqa: E501
        else:
            # Generate a deterministic private key for other indices
            private_key = f'0x{account_index:064x}'

        return cls(w3, accounts[account_index], private_key)

    def get_balance(self) -> int:
        """Get ETH balance of the wallet."""
        return self.w3.eth.get_balance(self.from_address)

    def get_nonce(self) -> int:
        """Get current nonce for the wallet."""
        return self.w3.eth.get_transaction_count(self.from_address)

    def transfer_eth(self, to_address: str, amount: int) -> Transaction:
        """Transfer ETH to another address."""
        # Ensure addresses are checksummed
        to_address = to_checksum_address(to_address)

        nonce = self.get_nonce()

        # Build transaction
        tx = {
            'to': to_address,
            'value': amount,
            'gas': 21000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'chainId': self.network.chain_id,
        }

        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Mine a block to confirm the transaction
        self.w3.provider.ethereum_tester.mine_blocks(1)

        # Get transaction receipt
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)

        return Transaction(
            id=str(uuid.uuid4()),
            hash=tx_hash.hex(),
            from_address=self.from_address,
            to_address=to_address,
            amount=str(amount),
            chain_id=self.network.chain_id,
            token='ETH',
            status='confirmed' if receipt['status'] == 1 else 'failed',
            gas_used=str(receipt['gasUsed']),
            gas_price=str(tx['gasPrice']),
            fee=str(receipt['gasUsed'] * tx['gasPrice']),
        )

    def transfer_usdc(self, to_address: str, amount: int) -> Transaction:
        """Transfer USDC to another address (simulated)."""
        # Ensure addresses are checksummed
        to_address = to_checksum_address(to_address)

        # For testing, we'll simulate USDC transfer
        # In a real scenario, this would interact with USDC contract

        nonce = self.get_nonce()

        # Simulate USDC transfer with higher gas
        tx = {
            'to': to_address,  # In real scenario, this would be USDC contract
            'value': 0,  # No ETH value for token transfer
            'gas': 65000,  # Higher gas for token transfer
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
            'chainId': self.network.chain_id,
            'data': '0x',  # Empty data for simulation
        }

        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Mine a block to confirm the transaction
        self.w3.provider.ethereum_tester.mine_blocks(1)

        # Get transaction receipt
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)

        return Transaction(
            id=str(uuid.uuid4()),
            hash=tx_hash.hex(),
            from_address=self.from_address,
            to_address=to_address,
            amount=str(amount),
            chain_id=self.network.chain_id,
            token='USDC',
            status='confirmed' if receipt['status'] == 1 else 'failed',
            gas_used=str(receipt['gasUsed']),
            gas_price=str(tx['gasPrice']),
            fee=str(receipt['gasUsed'] * tx['gasPrice']),
        )

    def fund_address(self, address: str, amount: int) -> Transaction:
        """Fund an address with ETH (useful for testing)."""
        return self.transfer_eth(address, amount)

    def get_transaction_receipt(self, tx_hash: str) -> Optional[dict]:
        """Get transaction receipt."""
        try:
            return self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            return None
