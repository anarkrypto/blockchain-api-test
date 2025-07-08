import logging
from typing import List, Optional

from eth_typing import HexStr
from web3 import Web3
from web3.exceptions import BlockNotFound, TransactionNotFound
from web3.types import LogReceipt, TxData, TxReceipt

from app.constants import USDC_CONTRACTS, NetworkType
from app.schemas import Erc20Transfer, EthTransfer, TransactionResult
from app.utils.web3_provider import getWeb3Provider

TRANSFER_EVENT_SIGNATURE = Web3.keccak(
    text='Transfer(address,address,uint256)'
)
MIN_TRANSFER_EVENT_TOPICS = 3
ADDRESS_PADDING_START = 26  # Remove first 26 chars to get address from topic

logger = logging.getLogger(__name__)


class TransactionDetector:
    def __init__(self, network: NetworkType) -> None:
        """
        Initialize the transaction detector

        Args:
            network: Network type to connect to
        """
        self.w3 = getWeb3Provider(network)
        self.network = network
        self.usdc_address = USDC_CONTRACTS[network].lower()

    def detect_transaction(self, tx_hash: str) -> Optional[TransactionResult]:
        """
        Detect transaction transfers for ETH, USDC and other ERC20 tokens.

        Args:
            tx_hash: Transaction hash to analyze

        Returns:
            TransactionResult: Result containing transaction details,
            or None if transaction not found

        Raises:
            ValueError: If transaction hash is invalid
        """
        try:
            tx_hash_hex = self._validate_and_format_hash(tx_hash)

            # Get transaction details
            tx = self.w3.eth.get_transaction(tx_hash_hex)
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash_hex)

            result = self._create_base_result(tx)

            # Process ETH transfers
            self._process_eth_transfer(tx, result)

            # Process ERC20 transfers
            self._process_erc20_transfers(tx_receipt, result)

            # Set transaction type if none found
            if not result.transaction_type:
                result.transaction_type.append('OTHER')

            return result

        except (TransactionNotFound, BlockNotFound) as e:
            logger.error(f'Transaction {tx_hash} not found: {e}')
            return None
        except Exception as e:
            logger.error(f'Error processing transaction {tx_hash}: {e}')
            raise

    @staticmethod
    def _validate_and_format_hash(tx_hash: str) -> HexStr:
        """Validate and format transaction hash."""
        if not tx_hash:
            raise ValueError('Transaction hash cannot be empty')

        # Add 0x prefix if missing
        if not tx_hash.startswith('0x'):
            tx_hash = '0x' + tx_hash

        # Validate length (64 hex chars + 0x prefix)
        if len(tx_hash) != 66:
            raise ValueError(
                f'Invalid transaction hash length: {len(tx_hash)}'
            )

        try:
            return HexStr(tx_hash)
        except ValueError as e:
            raise ValueError(f'Invalid transaction hash format: {e}')

    @staticmethod
    def _create_base_result(tx: TxData) -> TransactionResult:
        """Create base transaction result object."""
        return TransactionResult(
            hash=tx['hash'].hex(),
            block_number=tx['blockNumber'],
            from_address=tx['from'],
            to_address=tx['to'],
            eth_transfer=[],
            usdc_transfer=[],
            transaction_type=[],
        )

    @staticmethod
    def _process_eth_transfer(tx: TxData, result: TransactionResult) -> None:
        """Process ETH transfers from transaction."""
        eth_value = tx['value']
        if eth_value > 0:
            result.eth_transfer.append(
                EthTransfer(
                    amount=eth_value,
                    from_address=tx['from'],
                    to_address=tx['to'],
                )
            )
            result.transaction_type.append('ETH_TRANSFER')

    def _process_erc20_transfers(
        self, tx_receipt: TxReceipt, result: TransactionResult
    ) -> None:
        """Process ERC20 token transfers from transaction receipt logs."""
        for log in tx_receipt['logs']:
            if self._is_transfer_event(log):
                transfer = self._parse_transfer_event(log)
                if transfer:
                    # Check if it's USDC
                    if log['address'].lower() == self.usdc_address:
                        result.usdc_transfer.append(transfer)
                        if 'USDC_TRANSFER' not in result.transaction_type:
                            result.transaction_type.append('USDC_TRANSFER')
                    # Could extend here for other ERC20 tokens

    @staticmethod
    def _is_transfer_event(log: LogReceipt) -> bool:
        """Check if log entry is a Transfer event."""
        return (
            len(log['topics']) >= MIN_TRANSFER_EVENT_TOPICS
            and log['topics'][0] == TRANSFER_EVENT_SIGNATURE
        )

    @staticmethod
    def _parse_transfer_event(log: LogReceipt) -> Optional[Erc20Transfer]:
        """
        Parse Transfer event log into Erc20Transfer object.

        Args:
            log: Transaction log entry

        Returns:
            Erc20Transfer object or None if parsing fails
        """
        try:
            token_address = log['address']

            # Extract addresses from topics (remove padding)
            from_address = (
                '0x' + log['topics'][1].hex()[ADDRESS_PADDING_START:]
            )
            to_address = '0x' + log['topics'][2].hex()[ADDRESS_PADDING_START:]

            # Decode amount from data
            value = int(log['data'].hex(), 16)

            return Erc20Transfer(
                amount=value,
                from_address=from_address,
                to_address=to_address,
                token_address=token_address,
            )

        except (ValueError, IndexError, KeyError) as e:
            logger.warning(f'Failed to parse transfer event: {e}')
            return None

    def get_supported_tokens(self) -> List[str]:
        """Get list of supported token addresses for this network."""
        return [self.usdc_address]

    def is_supported_token(self, token_address: str) -> bool:
        """Check if token address is supported."""
        return token_address.lower() in [
            addr.lower() for addr in self.get_supported_tokens()
        ]
