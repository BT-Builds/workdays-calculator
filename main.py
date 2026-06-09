"""Workdays Calculator API - Calculate business days between dates."""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import date, timedelta
from typing import List, Optional
import uvicorn
import os
import time

app = FastAPI(
    title="Workdays Calculator API",
    description="Calculate business days between two dates, excluding weekends and holidays",
    version="1.0.0"
)
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Auth and Rate Limiting
from fastapi.security import HTTPBearer, HTTPException as FastAPIHTTPException

security = HTTPBearer()
rate_limit_store = {}

def verify_api_key(credentials = Depends(security)):
    api_key = credentials.credentials
    expected_key = os.getenv("API_KEY", "demo-key-change-in-production")
    if api_key != expected_key:
        raise FastAPIHTTPException(status_code=401, detail="Invalid API key")
    return api_key

def check_rate_limit(api_key: str, max_requests: int = 100):
    current_time = time.time()
    if api_key not in rate_limit_store:
        rate_limit_store[api_key] = []
    rate_limit_store[api_key] = [t for t in rate_limit_store[api_key] if current_time - t < 60]
    if len(rate_limit_store[api_key]) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    rate_limit_store[api_key].append(current_time)

# Models
class WorkdaysRequest(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    weekend_days: Optional[List[int]] = Field([6, 7], description="Weekend days as numbers (1=Monday, 7=Sunday). Default: 6,7 (Sat,Sun)")
    country_code: Optional[str] = Field("US", description="ISO country code for holidays (US, UK, DE, etc.)")

class WorkdaysResponse(BaseModel):
    start_date: str
    end_date: str
    total_days: int
    workdays: int
    holidays: int
    weekends: int
    working_dates: List[str]

# Holiday data for common countries
HOLIDAYS = {
    "US": [
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-05-27",
        "2024-06-19", "2024-07-04", "2024-09-02", "2024-10-14",
        "2024-11-28", "2024-12-25",
        "2025-01-01", "2025-01-20", "2025-02-17", "2025-05-26",
        "2025-06-19", "2025-07-04", "2025-09-01", "2025-10-13",
        "2025-11-27", "2025-12-25",
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-05-25",
        "2026-06-19", "2026-07-04", "2026-09-07", "2026-10-12",
        "2026-11-26", "2026-12-25"
    ],
    "UK": [
        "2024-01-01", "2024-03-29", "2024-04-01", "2024-05-06",
        "2024-05-27", "2024-08-26", "2024-12-25", "2024-12-26",
        "2025-01-01", "2025-04-18", "2025-04-21", "2025-05-05",
        "2025-05-26", "2025-08-25", "2025-12-25", "2025-12-26",
        "2026-01-01", "2026-04-03", "2026-04-06", "2026-05-04",
        "2026-05-25", "2026-08-31", "2026-12-25", "2026-12-26"
    ]
}

def calculate_workdays_core(start_date: str, end_date: str, weekend_days: List[int], country_code: str) -> WorkdaysResponse:
    """Core workdays calculation logic."""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")
    
    if end < start:
        raise ValueError("End date must be after start date.")
    
    weekend_set = set(weekend_days)
    country_holidays = set(HOLIDAYS.get(country_code, set()))
    
    working_dates = []
    total_days = 0
    weekends = 0
    holidays_count = 0
    
    current = start
    while current <= end:
        total_days += 1
        day_num = current.isoweekday()  # 1=Monday, 7=Sunday
        
        # Skip weekends
        if day_num in weekend_set:
            weekends += 1
            current += timedelta(days=1)
            continue
            
        current_str = current.isoformat()
        
        # Skip holidays
        if current_str in country_holidays:
            holidays_count += 1
            current += timedelta(days=1)
            continue
            
        working_dates.append(current_str)
        current += timedelta(days=1)
    
    workdays = len(working_dates)
    
    return WorkdaysResponse(
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        workdays=workdays,
        holidays=holidays_count,
        weekends=weekends,
        working_dates=working_dates
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/calculate", response_model=WorkdaysResponse)
def calculate_workdays(request: WorkdaysRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    return calculate_workdays_core(
        request.start_date,
        request.end_date,
        request.weekend_days or [6, 7],
        request.country_code or "US"
    )

# Bulk endpoint models
class BulkWorkdaysRequest(BaseModel):
    items: List[WorkdaysRequest] = Field(..., max_items=1000, description="Array of workdays requests (max 1000)")

class BulkWorkdaysResponse(BaseModel):
    results: List[dict]
    total: int
    successful: int

@app.post("/bulk/calculate", response_model=BulkWorkdaysResponse)
def calculate_workdays_bulk(request: BulkWorkdaysRequest, api_key: str = Depends(verify_api_key)):
    check_rate_limit(api_key)
    
    results = []
    successful = 0
    
    for item in request.items:
        try:
            output = calculate_workdays_core(
                item.start_date,
                item.end_date,
                item.weekend_days or [6, 7],
                item.country_code or "US"
            )
            results.append({
                "input": item.model_dump(),
                "output": output.model_dump(),
                "error": None
            })
            successful += 1
        except ValueError as e:
            results.append({
                "input": item.model_dump(),
                "output": None,
                "error": str(e)
            })
        except Exception as e:
            results.append({
                "input": item.model_dump(),
                "output": None,
                "error": str(e)
            })
    
    return BulkWorkdaysResponse(
        results=results,
        total=len(request.items),
        successful=successful
    )

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)