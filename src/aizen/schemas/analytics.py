from pydantic import BaseModel
from typing import Optional
from datetime import date

class DailyFeeAnalyticsRequest(BaseModel):
    user_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class DailyFeeAnalyticsResponse(BaseModel):
    date: date
    clone_fee: float
    fee_earned: float