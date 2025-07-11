from typing import Annotated, List, Literal, Optional

from eth_utils.address import is_address
from pydantic import BaseModel, Field, field_validator

from app.constants import (
    MAX_ADDRESSES_TO_GENERATE_PER_REQUEST,
    MAX_ADDRESSES_TO_LIST_PER_REQUEST,
    MAX_TRANSACTIONS_TO_LIST_PER_REQUEST,
    TokenType,
)


def validate_ethereum_address(v: str) -> str:
    """Shared validator for Ethereum address format."""
    if not is_address(v):
        raise ValueError('Invalid Ethereum address format')
    return v


NonNegativeInt = Annotated[int, Field(ge=0)]


class KeyPair(BaseModel):
    address: str
    private_key: str


TransactionType = Literal['ETH_TRANSFER', 'USDC_TRANSFER', 'OTHER']


class GenerateAddressesRequest(BaseModel):
    quantity: Annotated[
        int, Field(gt=0, le=MAX_ADDRESSES_TO_GENERATE_PER_REQUEST)
    ] = MAX_ADDRESSES_TO_GENERATE_PER_REQUEST


class APIResponse(BaseModel):
    success: bool


class ListAddressesPaginationParams(BaseModel):
    skip: NonNegativeInt = 0
    limit: Annotated[
        int, Field(gt=0, le=MAX_ADDRESSES_TO_LIST_PER_REQUEST)
    ] = MAX_ADDRESSES_TO_LIST_PER_REQUEST


class GenerateAddressesResponse(APIResponse):
    generated: int
    total: int


class ListAddressesResponse(APIResponse):
    limit: int
    skip: int
    total: int
    addresses: List[str]


class ProcessTransactionRequest(BaseModel):
    hash: str


class Deposit(BaseModel):
    address: str
    amount: int
    token: TokenType

    @field_validator('address')
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        return validate_ethereum_address(v)


class ProcessTransactionResponse(APIResponse):
    hash: str
    network: str
    chain_id: int
    deposits: List[Deposit]


class WithdrawRequest(BaseModel):
    from_address: str
    to_address: str
    amount: int
    token: TokenType

    @field_validator('from_address', 'to_address')
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        return validate_ethereum_address(v)


class WithdrawResponse(APIResponse):
    hash: str
    from_address: str
    to_address: str
    amount: int
    token: TokenType
    network: str
    chain_id: int
    status: str
    gas_used: int | None = None
    gas_price: int | None = None
    fee: int | None = None


TransactionStatus = Literal['pending', 'confirmed', 'failed']


class TransactionSchema(BaseModel):
    hash: str
    from_address: str | None
    to_address: str | None
    amount: str
    chain_id: int
    token: str
    status: str
    gas_used: str | None
    gas_price: str | None
    fee: str | None
    created_at: str


class HistoryRequest(BaseModel):
    address: str
    token: TokenType
    skip: NonNegativeInt = 0
    limit: Annotated[
        int, Field(gt=0, le=MAX_TRANSACTIONS_TO_LIST_PER_REQUEST)
    ] = MAX_TRANSACTIONS_TO_LIST_PER_REQUEST

    @field_validator('address')
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        return validate_ethereum_address(v)


class HistoryResponse(APIResponse):
    address: str
    token: TokenType
    network: str
    chain_id: int
    limit: int
    skip: int
    total: int
    transactions: List[TransactionSchema]


class RawContract(BaseModel):
    value: int
    address: Optional[str]
    decimal: int


class TransactionEvent(BaseModel):
    blockNum: int
    hash: str
    from_address: str
    to_address: str
    amount: int
    token: str
    raw_contract: RawContract

    @field_validator('from_address', 'to_address')
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        return validate_ethereum_address(v)


class TransactionResult(BaseModel):
    hash: str
    block_number: int
    from_address: str
    to_address: str
    transfers: List[TransactionEvent]
    tokens: List[str]
