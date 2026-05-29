from fastapi import APIRouter, HTTPException, status, Depends

from database import products_collection, config_collection
from models.alert import AlertResponse, ThresholdRequest, ThresholdResponse
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

DEFAULT_THRESHOLD = 10
CONFIG_KEY = "alert_threshold"


async def _get_threshold() -> int:
    doc = await config_collection.find_one({"key": CONFIG_KEY})
    return doc["value"] if doc else DEFAULT_THRESHOLD


def _severity(stock: int, threshold: int) -> str:
    if stock < threshold * 0.25:
        return "critical"
    if stock < threshold * 0.5:
        return "warning"
    return "info"


@router.get("", response_model=list[AlertResponse])
async def get_alerts(_: dict = Depends(get_current_user)):
    threshold = await _get_threshold()
    alerts = []
    async for product in products_collection.find({"stock": {"$lt": threshold}}):
        stock = product.get("stock", 0)
        alerts.append(AlertResponse(
            productName=product["name"],
            currentStock=stock,
            severity=_severity(stock, threshold),
        ))
    return alerts


@router.put("/threshold", response_model=ThresholdResponse)
async def set_threshold(request: ThresholdRequest, _: dict = Depends(get_current_user)):
    if request.threshold < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be a non-negative integer",
        )
    await config_collection.update_one(
        {"key": CONFIG_KEY},
        {"$set": {"key": CONFIG_KEY, "value": request.threshold}},
        upsert=True,
    )
    return ThresholdResponse(threshold=request.threshold)
