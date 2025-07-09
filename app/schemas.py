from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field

from app.constants import (
    MAX_ADDRESSES_TO_GENERATE_PER_REQUEST,
    MAX_ADDRESSES_TO_LIST_PER_REQUEST,
    TokenType,
)

NonNegativeInt = Annotated[int, Field(ge=0)]


class KeyPair(BaseModel):
    address: str
    private_key: str


class EthTransfer(BaseModel):
    amount: int
    from_address: str
    to_address: str


class Erc20Transfer(BaseModel):
    token_address: str
    amount: int
    from_address: str
    to_address: str


TransactionType = Literal['ETH_TRANSFER', 'USDC_TRANSFER', 'OTHER']


class TransactionResult(BaseModel):
    hash: str
    block_number: int
    from_address: str
    to_address: Optional[str]
    eth_transfer: List[EthTransfer] = []
    usdc_transfer: List[Erc20Transfer] = []
    transaction_type: List[TransactionType] = []


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


class ProcessTransactionResponse(APIResponse):
    hash: str
    network: str
    chain_id: int
    deposits: List[Deposit]


TransactionStatus = Literal['pending', 'confirmed', 'failed']
