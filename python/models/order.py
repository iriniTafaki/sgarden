from pydantic import BaseModel


class OrderItem(BaseModel):
    productId: str
    quantity: int


class OrderRequest(BaseModel):
    items: list[OrderItem]
