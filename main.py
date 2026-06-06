"""
US Macro Data API — Real-time US economic indicators
Sources: Bureau of Labor Statistics (BLS) + World Bank
Endpoints: /gdp, /inflation, /unemployment, /jobs, /indicators, /country/{code}/gdp
"""
import time
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ── app setup ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="US Macro Data API",
    description=(
        "Real-time US macroeconomic indicators: GDP, CPI inflation, unemployment, "
        "and nonfarm payroll employment. Data sourced from the Bureau of Labor "
        "Statistics (BLS) and World Bank — both public domain."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── constants ─────────────────────────────────────────────────────────────
BLS_BASE       = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
WORLDBANK_BASE = "https://api.worldbank.org/v2"

# BLS series IDs
SERIES_CPI         = "CUUR0000SA0"       # CPI All Urban Consumers
SERIES_UNEMPLOYMENT = "LNS14000000"      # Unemployment rate
SERIES_PAYROLL      = "CES0000000001"    # Total nonfarm payroll
SERIES_SPENDING     = "CXU900000LB1203M" # Consumer spending

CURRENT_YEAR = str(datetime.now().year)
DEFAULT_START = str(datetime.now().year - 2)


# ── helpers ───────────────────────────────────────────────────────────────

def _normalize_bls(raw_data: list) -> list:
    """Flatten BLS nested {year, period, periodName, value} → {year, period, period_name, value}."""
    results = []
    for item in raw_data:
        try:
            results.append({
                "year": item.get("year"),
                "period": item.get("period"),
                "period_name": item.get("periodName"),
                "value": float(item.get("value", 0)),
            })
        except (ValueError, TypeError):
            results.append({
                "year": item.get("year"),
                "period": item.get("period"),
                "period_name": item.get("periodName"),
                "value": None,
            })
    return results


async def _bls_fetch(series_id: str, year_start: str, year_end: str) -> list:
    """GET BLS v1 API (no key required) and return normalized data list."""
    url = f"{BLS_BASE}{series_id}"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"BLS API error: HTTP {resp.status_code}")

    body = resp.json()
    if body.get("status") not in ("REQUEST_SUCCEEDED", "REQUEST_NOT_PROCESSED"):
        if body.get("status") == "REQUEST_FAILED":
            msgs = body.get("message", [])
            raise HTTPException(status_code=502, detail=f"BLS request failed: {msgs}")

    series_list = body.get("Results", {}).get("series", [])
    if not series_list:
        raise HTTPException(status_code=404, detail=f"No BLS data found for series {series_id}")

    raw = series_list[0].get("data", [])
    # v1 GET returns latest ~3 years; filter to requested range if needed
    if year_start or year_end:
        raw = [
            item for item in raw
            if (year_start <= item.get("year", "") <= year_end)
        ]
    return _normalize_bls(raw)


async def _worldbank_fetch(country: str, indicator: str, limit: int = 5) -> list:
    """GET World Bank indicator data and return clean list."""
    url = (
        f"{WORLDBANK_BASE}/country/{country}/indicator/{indicator}"
        f"?format=json&per_page={limit}&mrv={limit}"
    )
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"World Bank API error: HTTP {resp.status_code}")

    body = resp.json()
    # World Bank returns [ metadata_dict, data_list ]
    if not isinstance(body, list) or len(body) < 2:
        raise HTTPException(status_code=502, detail="Unexpected World Bank response format")

    raw = body[1] or []
    results = []
    for item in raw:
        results.append({
            "year": item.get("date"),
            "value": item.get("value"),
            "country": item.get("country", {}).get("value"),
            "country_code": item.get("countryiso3code"),
            "indicator": item.get("indicator", {}).get("id"),
            "indicator_name": item.get("indicator", {}).get("value"),
            "unit": "USD",
        })
    return results


# ── routes ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    """Health check — confirms the API is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ping", tags=["System"])
async def ping():
    """Lightweight ping endpoint."""
    return {"pong": True}


@app.get("/", tags=["System"])
async def root():
    """API info and available endpoints."""
    return {
        "name": "US Macro Data API",
        "version": "1.0.0",
        "description": "Real-time US macroeconomic indicators from BLS and World Bank",
        "sources": ["Bureau of Labor Statistics (BLS)", "World Bank"],
        "endpoints": {
            "GET /gdp":                   "US GDP from World Bank",
            "GET /inflation":             "US CPI (inflation) from BLS",
            "GET /unemployment":          "US unemployment rate from BLS",
            "GET /jobs":                  "US nonfarm payroll from BLS",
            "GET /indicators":            "Combined macro snapshot",
            "GET /country/{code}/gdp":    "GDP for any World Bank country code",
            "GET /health":                "Health check",
            "GET /ping":                  "Ping",
            "GET /docs":                  "Swagger UI",
        },
        "pricing": {
            "BASIC": {"price": "$0/mo",  "requests": "100/mo"},
            "PRO":   {"price": "$9/mo",  "requests": "1,000/mo"},
            "ULTRA": {"price": "$29/mo", "requests": "10,000/mo"},
            "MEGA":  {"price": "$99/mo", "requests": "100,000/mo"},
        },
    }


@app.get("/gdp", tags=["Economic Indicators"])
async def get_gdp(
    country: str = Query(default="US", description="ISO country code (default: US)"),
    limit: int = Query(default=5, ge=1, le=20, description="Number of recent years to return"),
):
    """
    US GDP (or any country) from the World Bank.
    Indicator: NY.GDP.MKTP.CD (current USD).
    """
    data = await _worldbank_fetch(country.upper(), "NY.GDP.MKTP.CD", limit)
    return {
        "series": "NY.GDP.MKTP.CD",
        "series_name": "GDP (current US$)",
        "country": country.upper(),
        "source": "World Bank",
        "count": len(data),
        "data": data,
    }


@app.get("/inflation", tags=["Economic Indicators"])
async def get_inflation(
    year_start: str = Query(default=DEFAULT_START, description="Start year (e.g. 2022)"),
    year_end: str = Query(default=CURRENT_YEAR, description="End year (e.g. 2025)"),
):
    """
    US CPI (Consumer Price Index) — inflation proxy.
    BLS series: CUUR0000SA0 (CPI-U All Urban Consumers, All Items, Not Seasonally Adjusted).
    """
    data = await _bls_fetch(SERIES_CPI, year_start, year_end)
    return {
        "series_id": SERIES_CPI,
        "series_name": "CPI-U All Urban Consumers",
        "unit": "Index (1982-84=100)",
        "source": "Bureau of Labor Statistics",
        "year_start": year_start,
        "year_end": year_end,
        "count": len(data),
        "data": data,
    }


@app.get("/unemployment", tags=["Economic Indicators"])
async def get_unemployment(
    year_start: str = Query(default=DEFAULT_START, description="Start year (e.g. 2022)"),
    year_end: str = Query(default=CURRENT_YEAR, description="End year (e.g. 2025)"),
):
    """
    US unemployment rate (monthly, seasonally adjusted).
    BLS series: LNS14000000.
    """
    data = await _bls_fetch(SERIES_UNEMPLOYMENT, year_start, year_end)
    return {
        "series_id": SERIES_UNEMPLOYMENT,
        "series_name": "Unemployment Rate",
        "unit": "Percent",
        "seasonal_adjustment": "Seasonally Adjusted",
        "source": "Bureau of Labor Statistics",
        "year_start": year_start,
        "year_end": year_end,
        "count": len(data),
        "data": data,
    }


@app.get("/jobs", tags=["Economic Indicators"])
async def get_jobs(
    year_start: str = Query(default=DEFAULT_START, description="Start year (e.g. 2022)"),
    year_end: str = Query(default=CURRENT_YEAR, description="End year (e.g. 2025)"),
):
    """
    US Total Nonfarm Payroll Employment (monthly, seasonally adjusted).
    BLS series: CES0000000001.
    """
    data = await _bls_fetch(SERIES_PAYROLL, year_start, year_end)
    return {
        "series_id": SERIES_PAYROLL,
        "series_name": "Total Nonfarm Payroll Employment",
        "unit": "Thousands of persons",
        "seasonal_adjustment": "Seasonally Adjusted",
        "source": "Bureau of Labor Statistics",
        "year_start": year_start,
        "year_end": year_end,
        "count": len(data),
        "data": data,
    }


@app.get("/indicators", tags=["Economic Indicators"])
async def get_indicators():
    """
    Combined macro snapshot — latest GDP, unemployment rate, CPI, and nonfarm payroll.
    Fetches all four series concurrently for fast response.
    """
    current_year = str(datetime.now().year)
    prev_year = str(datetime.now().year - 1)

    # Fetch all in parallel
    gdp_task          = _worldbank_fetch("US", "NY.GDP.MKTP.CD", 1)
    unemployment_task = _bls_fetch(SERIES_UNEMPLOYMENT, prev_year, current_year)
    cpi_task          = _bls_fetch(SERIES_CPI, prev_year, current_year)
    payroll_task      = _bls_fetch(SERIES_PAYROLL, prev_year, current_year)

    gdp_data, unemployment_data, cpi_data, payroll_data = await asyncio.gather(
        gdp_task, unemployment_task, cpi_task, payroll_task,
        return_exceptions=True,
    )

    def _safe_latest(result, fallback_key="value"):
        if isinstance(result, Exception):
            return {"error": str(result)}
        if result:
            return result[0]
        return {}

    return {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "source": "BLS + World Bank",
        "gdp": {
            "series": "NY.GDP.MKTP.CD",
            "series_name": "GDP (current US$)",
            "unit": "USD",
            "latest": _safe_latest(gdp_data),
        },
        "unemployment": {
            "series_id": SERIES_UNEMPLOYMENT,
            "series_name": "Unemployment Rate",
            "unit": "Percent",
            "latest": _safe_latest(unemployment_data),
        },
        "cpi": {
            "series_id": SERIES_CPI,
            "series_name": "CPI-U All Urban Consumers",
            "unit": "Index (1982-84=100)",
            "latest": _safe_latest(cpi_data),
        },
        "payroll": {
            "series_id": SERIES_PAYROLL,
            "series_name": "Total Nonfarm Payroll Employment",
            "unit": "Thousands of persons",
            "latest": _safe_latest(payroll_data),
        },
    }


@app.get("/country/{country_code}/gdp", tags=["Economic Indicators"])
async def get_country_gdp(
    country_code: str,
    limit: int = Query(default=5, ge=1, le=20, description="Number of recent years"),
):
    """
    GDP (current USD) for any World Bank country code.
    Examples: US, GB, DE, JP, CN, IN, BR, CA, AU, FR.
    """
    data = await _worldbank_fetch(country_code.upper(), "NY.GDP.MKTP.CD", limit)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No GDP data found for country code '{country_code.upper()}'. "
                   "Check the World Bank country code (ISO2 or ISO3).",
        )
    return {
        "series": "NY.GDP.MKTP.CD",
        "series_name": "GDP (current US$)",
        "country_code": country_code.upper(),
        "source": "World Bank",
        "count": len(data),
        "data": data,
    }
