"""
US Macro Data API — Real-time US economic indicators
Source: World Bank (all endpoints)
Endpoints: /gdp, /inflation, /unemployment, /labor, /indicators, /country/{code}/gdp
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
        "and labor force participation. All data sourced from the World Bank — "
        "public domain, no API key required."
    ),
    version="2.0.0",
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
WORLDBANK_BASE = "https://api.worldbank.org/v2"

# World Bank indicator IDs
WB_GDP_USD         = "NY.GDP.MKTP.CD"    # GDP (current US$)
WB_GDP_GROWTH      = "NY.GDP.MKTP.KD.ZG" # GDP growth (annual %)
WB_INFLATION       = "FP.CPI.TOTL.ZG"   # CPI inflation (annual %)
WB_UNEMPLOYMENT    = "SL.UEM.TOTL.ZS"   # Unemployment (% of labor force)
WB_LABOR_FORCE     = "SL.TLF.CACT.ZS"   # Labor force participation (% ages 15+)
WB_EMPLOYMENT_POP  = "SL.EMP.TOTL.SP.ZS" # Employment to population ratio (%)


# ── helpers ───────────────────────────────────────────────────────────────

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
        "version": "2.0.0",
        "description": "Real-time US macroeconomic indicators. All data sourced from the World Bank.",
        "sources": ["World Bank"],
        "endpoints": {
            "GET /gdp":                   "US GDP (current USD) from World Bank",
            "GET /inflation":             "US CPI inflation (annual %) from World Bank",
            "GET /unemployment":          "US unemployment rate from World Bank",
            "GET /labor":                 "US labor force participation + employment ratio from World Bank",
            "GET /indicators":            "Combined macro snapshot (all 4 series)",
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
    data = await _worldbank_fetch(country.upper(), WB_GDP_USD, limit)
    return {
        "series": WB_GDP_USD,
        "series_name": "GDP (current US$)",
        "country": country.upper(),
        "source": "World Bank",
        "count": len(data),
        "data": data,
    }


@app.get("/inflation", tags=["Economic Indicators"])
async def get_inflation(
    country: str = Query(default="US", description="ISO country code (default: US)"),
    limit: int = Query(default=5, ge=1, le=20, description="Number of recent years to return"),
):
    """
    CPI inflation (annual % change) from the World Bank.
    Indicator: FP.CPI.TOTL.ZG.
    """
    data = await _worldbank_fetch(country.upper(), WB_INFLATION, limit)
    return {
        "series": WB_INFLATION,
        "series_name": "Inflation, consumer prices (annual %)",
        "unit": "Annual % change",
        "country": country.upper(),
        "source": "World Bank",
        "count": len(data),
        "data": data,
    }


@app.get("/unemployment", tags=["Economic Indicators"])
async def get_unemployment(
    country: str = Query(default="US", description="ISO country code (default: US)"),
    limit: int = Query(default=5, ge=1, le=20, description="Number of recent years to return"),
):
    """
    Unemployment rate (% of labor force) from the World Bank.
    Indicator: SL.UEM.TOTL.ZS.
    """
    data = await _worldbank_fetch(country.upper(), WB_UNEMPLOYMENT, limit)
    return {
        "series": WB_UNEMPLOYMENT,
        "series_name": "Unemployment, total (% of total labor force)",
        "unit": "% of labor force",
        "country": country.upper(),
        "source": "World Bank",
        "count": len(data),
        "data": data,
    }


@app.get("/labor", tags=["Economic Indicators"])
async def get_labor(
    country: str = Query(default="US", description="ISO country code (default: US)"),
    limit: int = Query(default=5, ge=1, le=20, description="Number of recent years to return"),
):
    """
    Labor market indicators from the World Bank:
    - Labor force participation rate (SL.TLF.CACT.ZS, % of population ages 15+)
    - Employment to population ratio (SL.EMP.TOTL.SP.ZS, % of population ages 15+)
    """
    lfp_task = _worldbank_fetch(country.upper(), WB_LABOR_FORCE, limit)
    emp_task = _worldbank_fetch(country.upper(), WB_EMPLOYMENT_POP, limit)

    lfp_data, emp_data = await asyncio.gather(lfp_task, emp_task, return_exceptions=True)

    def _safe(result):
        if isinstance(result, Exception):
            return {"error": str(result), "data": []}
        return {"count": len(result), "data": result}

    return {
        "country": country.upper(),
        "source": "World Bank",
        "labor_force_participation": {
            "series": WB_LABOR_FORCE,
            "series_name": "Labor force participation rate, total (% of total population ages 15+)",
            "unit": "% of population ages 15+",
            **_safe(lfp_data),
        },
        "employment_to_population": {
            "series": WB_EMPLOYMENT_POP,
            "series_name": "Employment to population ratio, 15+, total (%) (modeled ILO estimate)",
            "unit": "% of population ages 15+",
            **_safe(emp_data),
        },
    }


@app.get("/indicators", tags=["Economic Indicators"])
async def get_indicators(
    country: str = Query(default="US", description="ISO country code (default: US)"),
):
    """
    Combined macro snapshot — latest GDP, inflation, unemployment, and labor force participation.
    Fetches all four World Bank series concurrently for fast response.
    """
    cc = country.upper()

    gdp_task          = _worldbank_fetch(cc, WB_GDP_USD, 1)
    gdp_growth_task   = _worldbank_fetch(cc, WB_GDP_GROWTH, 1)
    inflation_task    = _worldbank_fetch(cc, WB_INFLATION, 1)
    unemployment_task = _worldbank_fetch(cc, WB_UNEMPLOYMENT, 1)

    gdp_data, gdp_growth_data, inflation_data, unemployment_data = await asyncio.gather(
        gdp_task, gdp_growth_task, inflation_task, unemployment_task,
        return_exceptions=True,
    )

    def _safe_latest(result):
        if isinstance(result, Exception):
            return {"error": str(result)}
        if result:
            return result[0]
        return {}

    return {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "country": cc,
        "source": "World Bank",
        "gdp": {
            "series": WB_GDP_USD,
            "series_name": "GDP (current US$)",
            "unit": "USD",
            "latest": _safe_latest(gdp_data),
        },
        "gdp_growth": {
            "series": WB_GDP_GROWTH,
            "series_name": "GDP growth (annual %)",
            "unit": "Annual %",
            "latest": _safe_latest(gdp_growth_data),
        },
        "inflation": {
            "series": WB_INFLATION,
            "series_name": "Inflation, consumer prices (annual %)",
            "unit": "Annual %",
            "latest": _safe_latest(inflation_data),
        },
        "unemployment": {
            "series": WB_UNEMPLOYMENT,
            "series_name": "Unemployment, total (% of total labor force)",
            "unit": "% of labor force",
            "latest": _safe_latest(unemployment_data),
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
    data = await _worldbank_fetch(country_code.upper(), WB_GDP_USD, limit)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No GDP data found for country code '{country_code.upper()}'. "
                   "Check the World Bank country code (ISO2 or ISO3).",
        )
    return {
        "series": WB_GDP_USD,
        "series_name": "GDP (current US$)",
        "country_code": country_code.upper(),
        "source": "World Bank",
        "count": len(data),
        "data": data,
    }
