from typing import List

from fastapi import Depends, FastAPI

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

# Temporary in-memory storage (not persistent)
generated_addresses: List[str] = []


@app.post('/addresses', tags=['items'])
async def generate_addresses(
    req: GenerateAddressesRequest,
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
    total_before = len(generated_addresses)

    for i in range(req.quantity):
        index = total_before + i
        keypair = generate_keypair(index)
        generated_addresses.append(keypair.address)

    return GenerateAddressesResponse(
        success=True,
        generated=req.quantity,
        total=len(generated_addresses),
    )


@app.get('/addresses')
async def list_addresses(
    params: ListAddressesPaginationParams = Depends(),
) -> ListAddressesResponse:
    """
    List previously generated Ethereum addresses.

    Supports pagination using `skip` and `limit` query parameters.
    \f
    :param params: Pagination parameters including skip and limit.
    """

    skip, limit = params.skip, params.limit

    return ListAddressesResponse(
        success=True,
        limit=limit,
        skip=skip,
        total=len(generated_addresses),
        addresses=generated_addresses[skip : skip + limit],
    )
