from pydantic import BaseModel
from datetime import date


class OrderResponse(BaseModel):
    id: int
    order_number: str
    order_date: date
    customer_name: str
    contact_phone: str
    email: str
    shipping_address: str
    gift_message: str
    items_summary: str
    tracking_number: str
    delivery_status: str
    is_special_request: bool
    special_request_type: str
    refund_status: str
    refund_amount: float
    refund_date: date | None
    refund_reason: str
    package_notes: str
    feedback: str
    endorsement: str
    total_price: float
    financial_status: str

    model_config = {"from_attributes": True}


class OrderUpdate(BaseModel):
    package_notes: str | None = None
    feedback: str | None = None
    endorsement: str | None = None


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    stats: dict
