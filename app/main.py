from contextlib import asynccontextmanager
from threading import Thread
from typing import AsyncIterator, cast

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.constants import NETWORK, NETWORKS, TokenType
from app.database import get_db
from app.models import Address, Balance, ProcessedTransaction, Transaction
from app.schemas import (
    Deposit,
    GenerateAddressesRequest,
    GenerateAddressesResponse,
    HistoryRequest,
    HistoryResponse,
    ListAddressesPaginationParams,
    ListAddressesResponse,
    ProcessTransactionRequest,
    ProcessTransactionResponse,
    TransactionSchema,
    WithdrawRequest,
    WithdrawResponse,
)
from app.utils.balance import get_balance
from app.utils.keypair import generate_keypair
from app.utils.receipt_processor import ReceiptProcessor
from app.utils.token_detector import TokenDetector
from app.utils.wallet import Wallet

receipt_processor = ReceiptProcessor(network=NETWORK)


def start_receipt_processor() -> None:
    receipt_processor.start()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    thread = Thread(target=start_receipt_processor, daemon=True)
    thread.start()
    app.state.receipt_processor = receipt_processor
    yield
    receipt_processor.stop()
    thread.join()


app = FastAPI(
    title='Blockchain API',
    description='RESTful API for blockchain operations',
    version='0.1.0',
    lifespan=lifespan,
)


@app.post('/addresses')
async def generate_addresses(
    req: GenerateAddressesRequest,
    db: Session = Depends(get_db),
) -> GenerateAddressesResponse:
    """
    Generate Ethereum addresses.
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
    """

    if db.query(ProcessedTransaction).filter_by(hash=req.hash).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Transaction has already been processed.',
        )

    detector = TokenDetector(NETWORK)
    result = detector.analyze_transaction(req.hash)

    if len(result.transfers) == 0:
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
            deposits=[],
        )

    to_addresses = list(
        set([transfer.to_address.lower() for transfer in result.transfers])
    )

    existent_addresses = {
        row.address
        for row in db.query(Address.address)
        .filter(Address.address.in_(to_addresses))
        .all()
    }

    deposits = []

    for transfer in result.transfers:
        if transfer.to_address.lower() in existent_addresses:
            transaction = Transaction(
                hash=req.hash,
                from_address=transfer.from_address.lower(),
                to_address=transfer.to_address.lower(),
                amount=transfer.amount,
                chain_id=NETWORKS[NETWORK].chain_id,
                token=transfer.token,
            )
            db.add(transaction)

            # Update Balance
            balance = (
                db.query(Balance)
                .filter_by(
                    address=transfer.to_address.lower(),
                    token=transfer.token,
                )
                .first()
            )
            if balance:
                balance.balance = str(
                    int(balance.balance) + int(transfer.amount)
                )
            else:
                balance = Balance(
                    address=transfer.to_address.lower(),
                    balance=str(transfer.amount),
                    token=transfer.token,
                    chain_id=NETWORKS[NETWORK].chain_id,
                )
                db.add(balance)

            db.commit()

            deposits.append(
                Deposit(
                    address=transfer.to_address.lower(),
                    amount=transfer.amount,
                    token=cast(TokenType, transfer.token),
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


@app.post('/withdraw')
async def withdraw(
    req: WithdrawRequest,
    db: Session = Depends(get_db),
) -> WithdrawResponse:
    """
    Withdraw assets from one address to another.
    """

    # Lock row for update to avoid race condition
    address = (
        db.query(Address)
        .filter_by(address=req.from_address)
        .with_for_update()
        .first()
    )
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Address not found.',
        )
    if req.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid amount.',
        )

    balance = get_balance(req.from_address, NETWORK, req.token)

    if balance < req.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Insufficient funds.',
        )

    chain_id = NETWORKS[NETWORK].chain_id

    wallet = Wallet(NETWORK, address.index)
    tx = wallet.transfer(
        req.token,
        req.to_address,
        req.amount,
    )
    db.add(tx)
    db.add(ProcessedTransaction(hash=tx.hash, chain_id=chain_id))
    db.commit()

    receipt_processor.add_pending_transaction(tx)

    # Balances updates will be done in the background
    # by the receipt_processor

    return WithdrawResponse(
        success=True,
        hash=tx.hash,
        from_address=req.from_address,
        to_address=req.to_address,
        amount=req.amount,
        token=req.token,
        network=NETWORK,
        chain_id=chain_id,
        status='pending',
        gas_used=int(tx.gas_used or 0),
        gas_price=int(tx.gas_price or 0),
        fee=int(tx.fee or 0),
    )


@app.get('/history')
async def history(
    req: HistoryRequest,
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """
    Get transaction history for an address.
    Supports pagination using `skip` and `limit` query parameters.
    """
    address = db.query(Address).filter_by(address=req.address).first()
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Address not found.',
        )

    # Count total transactions for this address and token
    total = (
        db.query(Transaction)
        .filter(
            (Transaction.from_address == req.address)
            | (Transaction.to_address == req.address),
            Transaction.token == req.token,
            Transaction.chain_id == NETWORKS[NETWORK].chain_id,
        )
        .count()
    )

    # Get paginated transactions
    transactions = (
        db.query(Transaction)
        .filter(
            (Transaction.from_address == req.address)
            | (Transaction.to_address == req.address),
            Transaction.token == req.token,
            Transaction.chain_id == NETWORKS[NETWORK].chain_id,
        )
        .order_by(Transaction.created_at.desc())
        .offset(req.skip)
        .limit(req.limit)
        .all()
    )

    # Convert SQLAlchemy models to Pydantic schemas
    transaction_schemas = [
        TransactionSchema(
            hash=tx.hash,
            from_address=tx.from_address,
            to_address=tx.to_address,
            amount=tx.amount,
            chain_id=tx.chain_id,
            token=tx.token,
            status=tx.status,
            gas_used=tx.gas_used,
            gas_price=tx.gas_price,
            fee=tx.fee,
            created_at=str(tx.created_at),
        )
        for tx in transactions
    ]

    return HistoryResponse(
        success=True,
        address=req.address,
        network=NETWORK,
        chain_id=NETWORKS[NETWORK].chain_id,
        token=req.token,
        skip=req.skip,
        limit=req.limit,
        total=total,
        transactions=transaction_schemas,
    )
