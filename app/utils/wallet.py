import decimal
import uuid

from eth_account.types import TransactionDictType
from eth_utils.address import to_checksum_address
from fastapi import HTTPException, status
from web3.types import Nonce, Wei

from app.constants import NETWORKS, USDC_CONTRACTS, NetworkType, TokenType
from app.models import Transaction
from app.utils.keypair import generate_keypair
from app.utils.logger import logger
from app.utils.web3_provider import get_web3_provider

USDC_CONTRACT_TRANSFER_ABI = [
    {
        'inputs': [
            {'name': '_to', 'type': 'address'},
            {'name': '_value', 'type': 'uint256'},
        ],
        'name': 'transfer',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function',
    }
]


class Wallet:
    def __init__(self, network: NetworkType, account_index: int):
        self.w3 = get_web3_provider(network)
        self.network = NETWORKS[network]
        self.usdc_contract_address = USDC_CONTRACTS[network]
        self.from_address = to_checksum_address(
            generate_keypair(account_index).address
        )
        self.private_key = generate_keypair(account_index).private_key

    def check_web3_provider(self) -> None:
        if not self.w3.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Web3 provider is not connected.',
            )

    def get_nonce(self) -> int:
        return self.w3.eth.get_transaction_count(
            to_checksum_address(self.from_address)
        )

    def get_gas_price(self) -> int:
        # Calcular gas price com margem (ex: 1.2x do sugerido)
        base_gas_price = self.w3.eth.gas_price
        gas_price = int(
            decimal.Decimal(base_gas_price) * decimal.Decimal('1.2')
        )
        return gas_price

    def _transfer_eth(self, to_address: str, amount: int) -> Transaction:
        gas_price = self.get_gas_price()
        nonce = self.get_nonce()
        gas_used = 21000  # Default to ETH transfer
        tx: TransactionDictType = {
            'to': to_checksum_address(to_address),
            'value': amount,
            'gas': gas_used,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': self.network.chain_id,
        }
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return Transaction(
            id=str(uuid.uuid4()),
            hash=tx_hash.hex(),
            from_address=self.from_address,
            to_address=to_address,
            amount=str(amount),
            chain_id=self.network.chain_id,
            token='ETH',
            status='pending',
            gas_used=gas_used,
            gas_price=gas_price,
            fee=gas_used * gas_price,
        )

    def _transfer_usdc(self, to_address: str, amount: int) -> Transaction:
        # A standard USDC (ERC-20) transfer typically consumes
        # ~50,000 to 65,000 gas units under normal network conditions
        gas_used = 65000
        gas_price = self.get_gas_price()
        nonce = self.get_nonce()
        usdc_contract = self.w3.eth.contract(
            address=to_checksum_address(self.usdc_contract_address),
            abi=USDC_CONTRACT_TRANSFER_ABI,
        )
        tx = usdc_contract.functions.transfer(
            to_address,
            amount,
        ).build_transaction({
            'from': self.from_address,
            'gas': gas_used,
            'gasPrice': Wei(gas_price),
            'nonce': Nonce(nonce),
            'chainId': self.network.chain_id,
        })
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return Transaction(
            id=str(uuid.uuid4()),
            hash=tx_hash.hex(),
            from_address=self.from_address,
            to_address=to_address,
            amount=str(amount),
            chain_id=self.network.chain_id,
            token='ETH',
            status='pending',
            gas_used=gas_used,
            gas_price=gas_price,
            fee=gas_used * gas_price,
        )

    def transfer(
        self, token: TokenType, to_address: str, amount: int
    ) -> Transaction:
        self.check_web3_provider()
        try:
            if token == 'ETH':
                return self._transfer_eth(to_address, amount)
            elif token == 'USDC':
                return self._transfer_usdc(to_address, amount)
            else:
                raise HTTPException(
                    status_code=400, detail='Token não suportado.'
                )

        except Exception as e:
            logger.exception(e)
            raise e
