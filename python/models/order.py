from pydantic import BaseModel
from typing import Optional


class OrderItem(BaseModel):
    productId: str
    quantity: int


class OrderRequest(BaseModel):
    items: list[OrderItem]
