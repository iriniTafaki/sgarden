from pydantic import BaseModel
from typing import Literal

class AlertResponse(BaseModel):
    productName: str
    currentStock: int
    severity: Literal["critical", "warning", "info"]


class ThresholdRequest(BaseModel):
    threshold: int


class ThresholdResponse(BaseModel):
    threshold: int
