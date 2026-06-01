# Workdays Calculator API

Calculate business days between two dates, excluding weekends and holidays.

## Problem it solves
Counting workdays between dates is a recurring task for payroll, contract duration, SLA calculations, and project planning. Developers end up writing and testing the same logic repeatedly.

## Who needs it
- HR/payroll software developers
- Contract management systems
- Project planning tools
- Anyone calculating SLA deadlines

## Endpoints

### GET /health
Health check endpoint (no auth required).

### POST /calculate
Calculate workdays between two dates.

**Request body:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "weekend_days": [6, 7],
  "country_code": "US"
}
```

**Response:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "total_days": 31,
  "workdays": 23,
  "holidays": 2,
  "weekends": 8,
  "working_dates": ["2024-01-02", "2024-01-03", ...]
}
```

## Try it

```bash
curl -X POST https://workdays-calculator.vercel.app/calculate \
  -H "Authorization: Bearer demo-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-31", "country_code": "US"}'
```

## Monetize
- RapidAPI listing: $19/mo for 1,000 requests
- Free tier: 100 requests/month
- Pro tier: 10,000 requests/month