from pydantic import BaseModel


class DashboardSummary(BaseModel):
    properties: int
    units: int
    active_leases: int
    open_work_orders: int
    unread_notifications: int
    subscription_plan: str
    subscription_status: str
