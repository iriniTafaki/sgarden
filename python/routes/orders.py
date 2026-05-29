from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from database import orders_collection, products_collection
from models.order import OrderRequest
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/orders", tags=["orders"])


def order_to_response(order: dict) -> dict:
    return {
        "id": str(order["_id"]),
        "items": order.get("items", []),
        "total": order.get("total"),
        "createdAt": order["createdAt"].isoformat() if order.get("createdAt") else None,
        "updatedAt": order["updatedAt"].isoformat() if order.get("updatedAt") else None,
    }


async def resolve_items(items) -> tuple[list[dict], float]:
    """Look up each product, build enriched item list, and compute total."""
    item_docs = []
    total = 0.0
    for item in items:
        if not ObjectId.is_valid(item.productId):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid productId: {item.productId}")
        product = await products_collection.find_one({"_id": ObjectId(item.productId)})
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Product {item.productId} not found")
        price = product.get("price", 0.0)
        item_docs.append({
            "productId": item.productId,
            "name": product.get("name"),
            "quantity": item.quantity,
            "price": price,
        })
        total += price * item.quantity
    return item_docs, round(total, 2)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(request: OrderRequest, current_user: dict = Depends(get_current_user)):
    item_docs, total = await resolve_items(request.items)
    now = datetime.utcnow()
    order_doc = {
        "items": item_docs,
        "total": total,
        "createdAt": now,
        "updatedAt": now,
    }
    result = await orders_collection.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id
    return order_to_response(order_doc)


@router.get("")
async def list_orders(current_user: dict = Depends(get_current_user)):
    orders = []
    async for order in orders_collection.find():
        orders.append(order_to_response(order))
    return orders


@router.get("/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order_to_response(order)


@router.put("/{order_id}")
async def update_order(order_id: str, request: OrderRequest,
                       current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    item_docs, total = await resolve_items(request.items)
    result = await orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"items": item_docs, "total": total, "updatedAt": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    return order_to_response(order)


@router.delete("/{order_id}")
async def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"message": "Order deleted"}
