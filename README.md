# 🇺🇸 US Macro Data API

![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=flat&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Data](https://img.shields.io/badge/Data-Public%20Domain-blue?style=flat)
![Sources](https://img.shields.io/badge/Sources-BLS%20%2B%20World%20Bank-orange?style=flat)

**Real-time US macroeconomic indicators via a clean REST API.** GDP, CPI inflation, unemployment rate, and nonfarm payroll — all in one place, sourced directly from the Bureau of Labor Statistics (BLS) and the World Bank. No API key required.

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8000

# Try it
curl http://localhost:8000/indicators
```

---

## 📊 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info + endpoint index |
| GET | `/health` | Health check `{status, timestamp}` |
| GET | `/ping` | Lightweight ping `{pong: true}` |
| GET | `/gdp` | US GDP from World Bank |
| GET | `/inflation` | US CPI (inflation) from BLS |
| GET | `/unemployment` | US unemployment rate from BLS |
| GET | `/jobs` | US nonfarm payroll from BLS |
| GET | `/indicators` | Combined macro snapshot (all 4 in one call) |
| GET | `/country/{code}/gdp` | GDP for any World Bank country code |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/redoc` | ReDoc API reference |

### Query Parameters

**GDP (`/gdp`, `/country/{code}/gdp`)**
- `country` — ISO country code, default `US`
- `limit` — number of years to return, default `5`, max `20`

**BLS series (`/inflation`, `/unemployment`, `/jobs`)**
- `year_start` — start year, default 2 years back
- `year_end` — end year, default current year

---

## 🔌 cURL Examples

```bash
# Health check
curl https://your-api.onrender.com/health

# Ping
curl https://your-api.onrender.com/ping

# Latest US GDP (5 years)
curl "https://your-api.onrender.com/gdp"

# US GDP, 10 years
curl "https://your-api.onrender.com/gdp?limit=10"

# CPI inflation 2022–2025
curl "https://your-api.onrender.com/inflation?year_start=2022&year_end=2025"

# Unemployment rate 2020–2025
curl "https://your-api.onrender.com/unemployment?year_start=2020&year_end=2025"

# Nonfarm payroll 2023–2025
curl "https://your-api.onrender.com/jobs?year_start=2023&year_end=2025"

# Full macro snapshot (all indicators, latest values)
curl "https://your-api.onrender.com/indicators"

# GDP for Germany
curl "https://your-api.onrender.com/country/DE/gdp"

# GDP for Japan, 8 years
curl "https://your-api.onrender.com/country/JP/gdp?limit=8"
```

---

## 📦 Example Responses

### `GET /indicators`
```json
{
  "snapshot_at": "2025-06-06T12:00:00+00:00",
  "source": "BLS + World Bank",
  "gdp": {
    "series": "NY.GDP.MKTP.CD",
    "series_name": "GDP (current US$)",
    "unit": "USD",
    "latest": {
      "year": "2023",
      "value": 27360935000000.0,
      "country": "United States",
      "country_code": "USA"
    }
  },
  "unemployment": {
    "series_id": "LNS14000000",
    "series_name": "Unemployment Rate",
    "unit": "Percent",
    "latest": { "year": "2025", "period": "M04", "period_name": "April", "value": 4.2 }
  },
  "cpi": {
    "series_id": "CUUR0000SA0",
    "series_name": "CPI-U All Urban Consumers",
    "unit": "Index (1982-84=100)",
    "latest": { "year": "2025", "period": "M04", "period_name": "April", "value": 317.8 }
  },
  "payroll": {
    "series_id": "CES0000000001",
    "series_name": "Total Nonfarm Payroll Employment",
    "unit": "Thousands of persons",
    "latest": { "year": "2025", "period": "M04", "period_name": "April", "value": 159472.0 }
  }
}
```

### `GET /jobs?year_start=2024&year_end=2025`
```json
{
  "series_id": "CES0000000001",
  "series_name": "Total Nonfarm Payroll Employment",
  "unit": "Thousands of persons",
  "seasonal_adjustment": "Seasonally Adjusted",
  "source": "Bureau of Labor Statistics",
  "year_start": "2024",
  "year_end": "2025",
  "count": 16,
  "data": [
    { "year": "2025", "period": "M04", "period_name": "April", "value": 159472.0 },
    { "year": "2025", "period": "M03", "period_name": "March", "value": 159286.0 }
  ]
}
```

---

## 💰 Pricing Tiers

| Tier | Price | Requests / Month | Features |
|------|-------|-----------------|----------|
| **BASIC** | $0 | 100 | All endpoints, public data |
| **PRO** | $9/mo | 1,000 | All endpoints + priority support |
| **ULTRA** | $29/mo | 10,000 | All endpoints + SLA |
| **MEGA** | $99/mo | 100,000 | All endpoints + dedicated support |

---

## 🗄️ Data Sources

| Source | Data | License |
|--------|------|---------|
| [Bureau of Labor Statistics (BLS)](https://www.bls.gov/developers/) | CPI, Unemployment, Payroll | Public Domain (US Government) |
| [World Bank Open Data](https://data.worldbank.org/) | GDP (NY.GDP.MKTP.CD) | CC BY 4.0 |

All data is **public domain** or **Creative Commons** licensed. No redistribution restrictions.

### BLS Series IDs Used

| Series ID | Description |
|-----------|-------------|
| `CUUR0000SA0` | CPI-U All Urban Consumers, All Items (Not Seasonally Adjusted) |
| `LNS14000000` | Unemployment Rate (Seasonally Adjusted) |
| `CES0000000001` | Total Nonfarm Payroll Employment (Seasonally Adjusted) |
| `CXU900000LB1203M` | Consumer Expenditures (reference) |

---

## 🛠️ Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — async Python web framework
- **[httpx](https://www.python-httpx.org/)** — async HTTP client
- **[Uvicorn](https://www.uvicorn.org/)** — ASGI server
- **Python 3.11+**

---

## 🚢 Deploy to Render

1. Push to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Done ✅

---

## 📝 License

MIT — free for personal and commercial use. Data is public domain from US government sources.
