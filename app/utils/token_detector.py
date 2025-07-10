from typing import List

from eth_typing import HexStr
from eth_utils.currency import to_wei
from web3.types import RPCEndpoint, TxData

from app.constants import USDC_CONTRACTS, NetworkType
from app.schemas import RawContract, TransactionEvent, TransactionResult
from app.utils.logger import logger
from app.utils.web3_provider import get_web3_provider


class TokenDetector:
    def __init__(self, network: NetworkType) -> None:
        self.w3 = get_web3_provider(network)
        self.network = network
        self.usdc_address = USDC_CONTRACTS[network].lower()

    def analyze_transaction(self, tx_hash: str) -> TransactionResult:
        """
        Analyze a specific transaction and return its asset transfers

        Args:
            tx_hash: Transaction hash to analyze

        Returns:
            Dictionary containing filtered asset transfers for this transaction
        """
        try:
            # Get transaction details to determine the block
            tx_details = self._get_transaction_details(tx_hash)

            print('tx_details', tx_details)

            block_number = tx_details['blockNumber']
            if not block_number:
                raise ValueError(
                    f'Block number not found for transaction {tx_hash}'
                )

            block_number_hex = hex(block_number)

            # Get all asset transfers for that block
            transfers_data = self._get_asset_transfers_for_block(
                block_number_hex
            )

            # Filter transfers to only include this specific transaction
            filtered_transfers = self._filter_transfers(
                transfers_data, tx_hash
            )

            tokens = self._get_tokens_found(filtered_transfers)

            return TransactionResult(
                hash=tx_hash.lower(),
                block_number=block_number,
                from_address=tx_details['from'].lower(),
                to_address=tx_details['to'].lower(),
                transfers=filtered_transfers,
                tokens=tokens,
            )

        except Exception as e:
            logger.error(f'Failed to analyze transaction: {e}')
            raise ValueError(f'Failed to analyze transaction: {str(e)}')

    def _get_transaction_details(self, tx_hash: str) -> TxData:
        try:
            tx = self.w3.eth.get_transaction(HexStr(tx_hash))

            return tx

        except Exception as e:
            logger.error(f'Failed to get transaction details: {e}')
            raise e

    def _get_asset_transfers_for_block(
        self, block_number: str
    ) -> List[TransactionEvent]:
        try:
            # This custom RPC endpoint only works with Alchemy provider
            # TODO: Add pagination
            response = self.w3.manager.request_blocking(
                RPCEndpoint('alchemy_getAssetTransfers'),
                [
                    {
                        'fromBlock': block_number,
                        'toBlock': block_number,
                        'category': ['external', 'internal', 'erc20'],
                        'excludeZeroValue': True,
                    }
                ],
            )

            if 'transfers' not in response:
                raise ValueError('Invalid response from Alchemy API')

            converted_transfers = []
            for transfer in response.transfers:
                if transfer.asset is None:
                    continue
                new_transfer = TransactionEvent(
                    blockNum=int(transfer.blockNum, 16),
                    hash=transfer.hash.lower(),
                    from_address=transfer['from'].lower(),
                    to_address=transfer.to.lower(),
                    amount=int(transfer.rawContract.value, 16),
                    token=transfer.asset,
                    raw_contract=RawContract(
                        value=int(transfer.rawContract.value, 16),
                        address=transfer.rawContract.address.lower()
                        if transfer.rawContract.address is not None
                        else None,
                        decimal=int(transfer.rawContract.decimal, 16),
                    ),
                )
                converted_transfers.append(new_transfer)

            return converted_transfers

        except Exception as e:
            logger.error(f'Failed to get asset transfers: {e}')
            raise e

    def _filter_transfers(  # noqa: PLR6301
        self,
        transfers: List[TransactionEvent],
        tx_hash: str,
    ) -> List[TransactionEvent]:
        # Filter transfers to only include the specific transaction
        # and transfers of ETH or USDC with the correct contract address

        tokens = ['ETH', 'USDC']

        filtered_transfers: List[TransactionEvent] = []

        for transfer in transfers:
            if (
                transfer.hash.lower() == tx_hash.lower()
                and transfer.token in tokens
            ):
                if transfer.token == 'USDC' and (
                    transfer.raw_contract.address is None
                    or transfer.raw_contract.address.lower()
                    != self.usdc_address
                ):
                    continue

                filtered_transfers.append(transfer)

        return filtered_transfers

    def _get_tokens_found(  # noqa: PLR6301
        self, transfers: List[TransactionEvent]
    ) -> List[str]:
        tokens: List[str] = []
        for transfer in transfers:
            if transfer.token not in tokens:
                tokens.append(transfer.token)
        return tokens
