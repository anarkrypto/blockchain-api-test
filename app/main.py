import uuid
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.constants import NETWORK, NETWORKS
from app.database import get_db
from app.models import Address, ProcessedTransaction, Transaction
from app.schemas import (
    Deposit,
    EthTransfer,
    GenerateAddressesRequest,
    GenerateAddressesResponse,
    ListAddressesPaginationParams,
    ListAddressesResponse,
    ProcessTransactionRequest,
    ProcessTransactionResponse,
)
from app.utils.keypair import generate_keypair
from app.utils.transaction_detector import TransactionDetector

app = FastAPI(
    title='Blockchain API',
    description='RESTful API for blockchain operations',
    version='0.1.0',
)


@app.post('/addresses', tags=['items'])
async def generate_addresses(
    req: GenerateAddressesRequest,
    db: Session = Depends(get_db),
) -> GenerateAddressesResponse:
    """
    Generate Ethereum addresses.

    Request body:

    - **quantity**: number of addresses to generate

    Returns:
     - **success**: boolean
     - **generated**: the number of addresses generated
     - **total**: the total of addresses accumulated.
    \f
    """
    total_before = db.query(Address).count()

    for i in range(req.quantity):
        index = total_before + i
        keypair = generate_keypair(index)
        address = Address(
            address=keypair.address.lower(),
            index=index,
        )
        db.add(address)

    db.commit()

    total_after = db.query(Address).count()

    return GenerateAddressesResponse(
        success=True,
        generated=req.quantity,
        total=total_after,
    )


@app.get('/addresses')
async def list_addresses(
    params: ListAddressesPaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> ListAddressesResponse:
    """
    List previously generated Ethereum addresses.

    Supports pagination using `skip` and `limit` query parameters.
    \f
    :param params: Pagination parameters including skip and limit.

    Returns:
        - **success**: boolean
        - **limit**: the number of addresses returned
        - **skip**: the number of addresses skipped
        - **total**: the total number of addresses
        - **addresses**: the list of addresses
    """

    skip, limit = params.skip, params.limit

    total = db.query(Address).count()

    addresses = (
        db.query(Address.address)
        .order_by(Address.index)
        .offset(skip)
        .limit(limit)
        .all()
    )

    addresses_list = [a[0] for a in addresses]

    return ListAddressesResponse(
        success=True,
        limit=limit,
        skip=skip,
        total=total,
        addresses=addresses_list,
    )


@app.post('/process-transaction')
async def process_transaction(
    req: ProcessTransactionRequest,
    db: Session = Depends(get_db),
) -> ProcessTransactionResponse:
    """
    Process a transaction by its hash.

    Request body:
    - **hash**: the hash of the transaction to process

    Returns:
     - **success**: boolean
     - **hash**: the hash of the transaction
     - **network**: the network of the transaction
     - **chain_id**: the chain ID of the network
     - **deposits**: list of deposits made by the transaction
    \f
    """

    if db.query(ProcessedTransaction).filter_by(hash=req.hash).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Transaction has already been processed.',
        )

    detector = TransactionDetector(NETWORK)
    result = detector.detect_transaction(req.hash)

    if (
        'ETH_TRANSFER' not in result.transaction_type
        and 'USDC_TRANSFER' not in result.transaction_type
    ):
        return ProcessTransactionResponse(
            success=True,
            hash=req.hash,
            network=NETWORK,
            chain_id=NETWORKS[NETWORK].chain_id,
            deposits=[],
        )

    all_transfers = result.eth_transfer + result.usdc_transfer
    to_addresses = list(
        set([item.to_address.lower() for item in all_transfers])
    )

    existent_addresses = {
        row.address
        for row in db.query(Address.address)
        .filter(Address.address.in_(to_addresses))
        .all()
    }

    deposits: List[Deposit] = []

    for transfer in all_transfers:
        if transfer.to_address.lower() in existent_addresses:
            token = 'ETH' if isinstance(transfer, EthTransfer) else 'USDC'
            transaction = Transaction(
                id=uuid.uuid4(),
                hash=req.hash,
                from_address=transfer.from_address.lower(),
                to_addresses=transfer.to_address.lower(),
                amount=transfer.amount,
                chain_id=NETWORKS[NETWORK].chain_id,
                token=token,
            )
            db.add(transaction)
            deposits.append(
                Deposit(
                    address=transfer.to_address.lower(),
                    amount=transfer.amount,
                    asset=token,
                )
            )

    db.add(
        ProcessedTransaction(
            hash=req.hash, chain_id=NETWORKS[NETWORK].chain_id
        )
    )

    db.commit()

    return ProcessTransactionResponse(
        success=True,
        hash=req.hash,
        network=NETWORK,
        chain_id=NETWORKS[NETWORK].chain_id,
        deposits=deposits,
    )
