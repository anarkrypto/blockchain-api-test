from typing import Any, Dict

from eth_utils.address import is_address
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas import GenerateAddressesResponse, ListAddressesResponse


def validate_response_schema(data: Dict[str, Any], schema_class: type) -> None:
    schema_class(**data)


def test_generate_addresses_successful_generation(client: TestClient) -> None:
    quantity = 10
    response = client.post('/addresses', json={'quantity': quantity})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    validate_response_schema(data, GenerateAddressesResponse)

    assert data['success'] is True
    assert data['generated'] == quantity
    assert data['total'] == quantity


def test_generate_addresses_accumulates_total(client: TestClient) -> None:
    quantity = 10

    # Generate first batch
    response = client.post('/addresses', json={'quantity': quantity})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    validate_response_schema(data, GenerateAddressesResponse)
    assert data['total'] == quantity

    # Generate second batch
    response2 = client.post('/addresses', json={'quantity': quantity})
    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()

    validate_response_schema(data2, GenerateAddressesResponse)
    assert data2['total'] == quantity * 2


def test_list_addresses_pagination(client: TestClient) -> None:
    # Setup: Create test data
    quantity = 15
    setup_response = client.post('/addresses', json={'quantity': quantity})
    assert setup_response.status_code == status.HTTP_200_OK

    # Test: Get paginated results
    skip = 0
    limit = 10
    response = client.get(f'/addresses?skip={skip}&limit={limit}')
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    validate_response_schema(data, ListAddressesResponse)

    assert data['success'] is True
    assert data['skip'] == skip
    assert data['limit'] == limit
    assert data['total'] == quantity
    assert len(data['addresses']) == limit

    for address in data['addresses']:
        assert is_address(address)


def test_generate_addresses_invalid_quantity(client: TestClient) -> None:
    response = client.post('/addresses', json={'quantity': -1})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_addresses_invalid_pagination(client: TestClient) -> None:
    response = client.get('/addresses?skip=-5&limit=0')
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
