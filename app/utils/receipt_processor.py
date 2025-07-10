from threading import Event
from typing import List

from eth_utils.address import to_checksum_address
from web3.exceptions import TransactionNotFound

from app.constants import NetworkType
from app.database import SessionLocal
from app.models import Balance, Transaction
from app.schemas import TransactionStatus
from app.utils.logger import logger
from app.utils.web3_provider import get_web3_provider


class ReceiptProcessor:
    def __init__(self, network: NetworkType):
        self.w3 = get_web3_provider(network)
        self.pending_transactions: List[Transaction] = []
        self.db = SessionLocal()
        self.started = False
        self._stop_event = Event()

    def _update_transaction(
        self, transaction: Transaction, tx_status: TransactionStatus
    ) -> None:
        transaction.status = tx_status
        self.pending_transactions.remove(transaction)

    def _update_balance(self, transaction: Transaction) -> None:
        balance = (
            self.db.query(Balance)
            .filter_by(
                address=transaction.to_address,
                chain_id=transaction.chain_id,
                token=transaction.token,
            )
            .first()
        )
        assert balance is not None
        assert transaction.fee is not None
        tx_spent = int(transaction.amount) + int(transaction.fee)
        balance.balance = str(int(balance.balance) - tx_spent)

    def _process_transaction(self, transaction: Transaction) -> None:
        self.pending_transactions.append(transaction)

        try:
            tx_receipt = self.w3.eth.get_transaction_receipt(
                to_checksum_address(transaction.hash)
            )
            if not tx_receipt or tx_receipt['status'] != 1:
                self._update_transaction(transaction, 'failed')
                return

            with self.db.begin():
                self._update_transaction(transaction, 'confirmed')
                self._update_balance(transaction)
        except TransactionNotFound:
            logger.warning(
                f'Transaction {transaction.hash} not found on chain'
            )

    def _sync_pending_transactions(self) -> None:
        pending_transactions = (
            self.db.query(Transaction)
            .filter(Transaction.status == 'pending')
            .all()
        )
        logger.info(f'Found {len(pending_transactions)} pending transactions')
        for transaction in pending_transactions:
            self.add_pending_transaction(transaction)

    def _process_pending_transactions(self) -> None:
        while self.started:
            for transaction in self.pending_transactions:
                try:
                    self._process_transaction(transaction)
                except Exception as e:
                    print(
                        f'Error processing transaction {transaction.hash}: {e}'
                    )
            self._stop_event.wait(10)  # Interruptible sleep

    def add_pending_transaction(self, transaction: Transaction) -> None:
        self.pending_transactions.append(transaction)

    def start(self) -> None:
        try:
            if self.started:
                return
            self.started = True
            self._stop_event.clear()
            logger.info('Starting ReceiptProcessor')
            self._sync_pending_transactions()
            self._process_pending_transactions()
        except Exception as e:
            logger.exception(f'Receipt processor failed to start: {e}')

    def stop(self) -> None:
        logger.info('Receipt processor stopped')
        self.started = False
        self._stop_event.set()
