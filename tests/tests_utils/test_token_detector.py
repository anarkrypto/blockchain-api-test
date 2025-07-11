"""
Test-specific TokenDetector that extends the original
for eth-tester compatibility.
"""

from typing import List, Optional

from web3 import Web3

from app.schemas import RawContract, TransactionEvent
from app.utils.logger import logger
from app.utils.token_detector import TokenDetector


class TestTokenDetector(TokenDetector):
    """TokenDetector extension for testing with eth-tester."""

    def __init__(self, w3: Optional[Web3] = None):
        """Initialize with optional eth-tester Web3 instance."""
        # If w3 is provided, use it; otherwise call parent constructor
        if w3 is not None:
            super().__init__('sepolia')
            self.w3 = w3
        else:
            super().__init__('sepolia')

        # Check if we're using eth-tester
        self.is_eth_tester = hasattr(self.w3.provider, 'ethereum_tester')

    def _get_asset_transfers_for_block(
        self, block_number: str
    ) -> List[TransactionEvent]:
        """Override to use eth-tester specific implementation."""
        if self.is_eth_tester:
            return self._get_eth_tester_transfers(block_number)
        else:
            # Fall back to original implementation for non-test environments
            return super()._get_asset_transfers_for_block(block_number)

    def _get_eth_tester_transfers(
        self, block_number: str
    ) -> List[TransactionEvent]:
        """Get transfers for eth-tester (simplified for testing)."""
        try:
            # Get the latest block
            latest_block = self.w3.eth.get_block(
                int(block_number, 16), full_transactions=True
            )

            transfers = []
            for tx in latest_block['transactions']:
                if tx.value > 0:  # Only ETH transfers
                    transfer = TransactionEvent(
                        blockNum=int(block_number, 16),
                        hash=tx.hash.hex().lower(),
                        from_address=tx['from'].lower(),
                        to_address=tx['to'].lower(),
                        amount=tx.value,
                        token='ETH',
                        raw_contract=RawContract(
                            value=tx.value,
                            address=None,
                            decimal=18,
                        ),
                    )
                    transfers.append(transfer)

            return transfers
        except Exception as e:
            logger.error(f'Failed to get eth-tester transfers: {e}')
            return []
