from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import products_collection
from models.product import ProductRequest
from security.jwt_handler import get_current_user


class StockUpdateRequest(BaseModel):
    stock: int

router = APIRouter(prefix="/api/products", tags=["products"])

# CODE QUALITY ISSUE: unused variable
service_name = "ProductService"

VALID_CATEGORIES = {"Electronics", "Accessories", "Storage", "Networking"}


def product_to_response(product: dict) -> dict:
    """Convert MongoDB document to API response format."""
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock": product.get("stock", 0),
        "createdAt": product.get("createdAt", "").isoformat() if product.get("createdAt") else None,
        "updatedAt": product.get("updatedAt", "").isoformat() if product.get("updatedAt") else None,
    }


def format_product(product: dict) -> dict:
    """CODE QUALITY ISSUE: duplicate of product_to_response above."""
    return {
        "id": str(product["_id"]),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
        "price": product.get("price"),
        "stock": product.get("stock", 0),
        "createdAt": product.get("createdAt", "").isoformat() if product.get("createdAt") else None,
        "updatedAt": product.get("updatedAt", "").isoformat() if product.get("updatedAt") else None,
    }


@router.get("")
async def get_all_products(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1),
    sort: Optional[str] = Query(default=None),
    order: Optional[str] = Query(default="asc"),
):
    print("Fetching all products")
    sort_field = sort or "_id"
    sort_direction = 1 if order != "desc" else -1
    total = await products_collection.count_documents({})
    skip = (page - 1) * limit
    cursor = products_collection.find().sort(sort_field, sort_direction).skip(skip).limit(limit)
    products = []
    async for product in cursor:
        products.append(product_to_response(product))
    return {"data": products, "page": page, "limit": limit, "total": total}


@router.get("/search")
async def search_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    minPrice: Optional[float] = None,
    maxPrice: Optional[float] = None,
):
    filters = []

    if q:
        filters.append({"$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]})

    if category:
        filters.append({"category": category})

    if minPrice is not None or maxPrice is not None:
        price_cond = {}
        if minPrice is not None:
            price_cond["$gte"] = minPrice
        if maxPrice is not None:
            price_cond["$lte"] = maxPrice
        filters.append({"price": price_cond})

    mongo_query = {"$and": filters} if filters else {}

    products = []
    async for product in products_collection.find(mongo_query):
        products.append(product_to_response(product))
    return products


@router.get("/stats")
async def get_product_stats():
    totals_cursor = products_collection.aggregate([
        {"$group": {
            "_id": None,
            "totalCount": {"$sum": 1},
            "averagePrice": {"$avg": "$price"},
            "minPrice": {"$min": "$price"},
            "maxPrice": {"$max": "$price"},
        }}
    ])
    totals = await totals_cursor.to_list(length=1)

    categories_cursor = products_collection.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ])
    categories = await categories_cursor.to_list(length=None)

    if not totals:
        return {"totalCount": 0, "averagePrice": 0, "minPrice": 0, "maxPrice": 0, "categoryCount": {}}

    stats = totals[0]
    category_count = {doc["_id"]: doc["count"] for doc in categories if doc["_id"] is not None}
    return {
        "totalCount": stats["totalCount"],
        "averagePrice": round(stats["averagePrice"] or 0, 2),
        "minPrice": stats["minPrice"],
        "maxPrice": stats["maxPrice"],
        "categoryCount": category_count,
    }


@router.get("/{product_id}")
async def get_product_by_id(product_id: str):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return product_to_response(product)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(request: ProductRequest, current_user: dict = Depends(get_current_user)):
    errors = {}
    if not request.name or not request.name.strip():
        errors["name"] = "Name must be a non-empty string"
    if request.price is not None and request.price <= 0:
        errors["price"] = "Price must be a positive number"
    if request.category is not None and request.category not in VALID_CATEGORIES:
        errors["category"] = "Category must be one of: Electronics, Accessories, Storage, Networking"
    if errors:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errors": errors})

    product_doc = {
        "name": request.name,
        "description": request.description,
        "category": request.category,
        "price": request.price,
        "stock": request.stock if request.stock is not None else 0,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await products_collection.insert_one(product_doc)
    product_doc["_id"] = result.inserted_id
    print(f"Created product: {request.name}")
    return product_to_response(product_doc)


async def update_product_legacy(product_id: str, request: ProductRequest, current_user: dict = Depends(get_current_user)):
    """CODE QUALITY ISSUE: duplicate of update_product."""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.category is not None:
        update_fields["category"] = request.category
    if request.price is not None:
        update_fields["price"] = request.price
    if request.stock is not None:
        update_fields["stock"] = request.stock

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_fields["updatedAt"] = datetime.utcnow()

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.put("/{product_id}")
async def update_product(product_id: str, request: ProductRequest, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    errors = {}
    if request.name is not None and not request.name.strip():
        errors["name"] = "Name must be a non-empty string"
    if request.price is not None and request.price <= 0:
        errors["price"] = "Price must be a positive number"
    if request.category is not None and request.category not in VALID_CATEGORIES:
        errors["category"] = "Category must be one of: Electronics, Accessories, Storage, Networking"
    if errors:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"errors": errors})

    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name
    if request.description is not None:
        update_fields["description"] = request.description
    if request.category is not None:
        update_fields["category"] = request.category
    if request.price is not None:
        update_fields["price"] = request.price
    if request.stock is not None:
        update_fields["stock"] = request.stock

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    update_fields["updatedAt"] = datetime.utcnow()

    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_fields},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.patch("/{product_id}/stock")
async def update_stock(product_id: str, request: StockUpdateRequest,
                       _: dict = Depends(get_current_user)):
    if request.stock < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Stock cannot be negative")
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    result = await products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"stock": request.stock, "updatedAt": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product = await products_collection.find_one({"_id": ObjectId(product_id)})
    return product_to_response(product)


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    result = await products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return {"message": "Product deleted"}
