from app.constants import NETWORKS, NetworkType
from app.database import SessionLocal
from app.models import Balance, Transaction


def get_balance(address: str, network: NetworkType, token: str) -> int:
    db = SessionLocal()
    chain_id = NETWORKS[network].chain_id
    balance = (
        db.query(Balance)
        .filter_by(address=address, token=token, chain_id=chain_id)
        .with_for_update()
        .first()
    )

    # get pending balance from pending transactions of this account address
    pending_transactions = (
        db.query(Transaction.amount, Transaction.fee)
        .filter_by(
            from_address=address,
            token=token,
            chain_id=chain_id,
            status='pending',
        )
        .with_for_update()
        .all()
    )

    # Calculate total balance
    total_balance = 0
    if balance:
        total_balance = int(balance.balance)
    for amount, fee in pending_transactions:
        total_balance += amount + (fee or 0)

    return total_balance
