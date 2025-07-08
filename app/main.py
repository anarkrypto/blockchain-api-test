from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Address
from app.schemas import (
    GenerateAddressesRequest,
    GenerateAddressesResponse,
    ListAddressesPaginationParams,
    ListAddressesResponse,
)
from app.utils.keypair import generate_keypair

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
