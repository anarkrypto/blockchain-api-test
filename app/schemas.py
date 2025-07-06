from pydantic import BaseModel


class KeyPair(BaseModel):
    address: str
    private_key: str
