from fastapi import APIRouter, Depends
from typing import Optional
from datetime import date, datetime, time

from database import orders_collection
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sales")
async def get_sales_analytics(
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
    current_user: dict = Depends(get_current_user),
):
    match_filter = {}
    if startDate or endDate:
        date_filter = {}
        if startDate:
            date_filter["$gte"] = datetime.combine(startDate, time.min)
        if endDate:
            date_filter["$lte"] = datetime.combine(endDate, time.max)
        match_filter["createdAt"] = date_filter

    totals_cursor = orders_collection.aggregate([
        {"$match": match_filter},
        {"$group": {"_id": None, "totalRevenue": {"$sum": "$total"}, "totalOrders": {"$sum": 1}}},
    ])
    totals_result = await totals_cursor.to_list(length=1)
    totals = totals_result[0] if totals_result else {"totalRevenue": 0, "totalOrders": 0}

    top_products_cursor = orders_collection.aggregate([
        {"$match": match_filter},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.productId",
            "name": {"$first": "$items.name"},
            "totalQuantity": {"$sum": "$items.quantity"},
            "totalRevenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
        }},
        {"$sort": {"totalRevenue": -1}},
        {"$limit": 10},
    ])
    top_products_raw = await top_products_cursor.to_list(length=10)
    top_products = [
        {
            "productId": item["_id"],
            "name": item["name"],
            "totalQuantity": item["totalQuantity"],
            "totalRevenue": round(item["totalRevenue"], 2),
        }
        for item in top_products_raw
    ]

    period_cursor = orders_collection.aggregate([
        {"$match": match_filter},
        {"$group": {
            "_id": {"year": {"$year": "$createdAt"}, "month": {"$month": "$createdAt"}},
            "revenue": {"$sum": "$total"},
            "orders": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ])
    period_raw = await period_cursor.to_list(length=None)
    revenue_by_period = [
        {
            "period": f"{item['_id']['year']}-{item['_id']['month']:02d}",
            "revenue": round(item["revenue"], 2),
            "orders": item["orders"],
        }
        for item in period_raw
    ]

    return {
        "totalRevenue": round(totals["totalRevenue"], 2),
        "totalOrders": totals["totalOrders"],
        "topProducts": top_products,
        "revenueByPeriod": revenue_by_period,
    }
