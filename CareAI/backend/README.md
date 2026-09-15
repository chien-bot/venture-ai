# CareAI Backend MVP

CareAI is an AI-assisted health-risk management service. It does not diagnose diseases or replace medical professionals.

## Included in this phase

- Adult basic health data validation: age, gender, height, weight, blood pressure, sleep and exercise frequency.
- Local, explainable rules for BMI, sleep, and exercise risks.
- School MaaS integration for `deepseek-v4-flash` using `GPUSTACK_API_KEY` from the environment.
- A constrained Health Report Agent: the rule engine fixes risk levels, while the LLM only writes explanations, suggestions, and a 7-day plan.
- Versioned, reviewable rule configuration with public-health reference links and a clinical-review notice.

## Run locally (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:GPUSTACK_API_KEY = "your_school_maas_api_key"
uvicorn app.main:app --reload
```

### Use OpenRouter instead of school MaaS

```powershell
$env:LLM_PROVIDER = "openrouter"
$env:OPENROUTER_API_KEY = "your_openrouter_api_key"
$env:LLM_MODEL = "deepseek/deepseek-v4-flash"
uvicorn app.main:app --reload
```

Keep API keys in environment variables only. Do not put them in frontend files or commit them.

Open interactive API documentation at `http://127.0.0.1:8000/docs`.

## Rule transparency and safety

`GET /api/v1/health/rule-info` returns the active rule version, thresholds, scope, review notice, and public-health references. This makes the MVP rule engine inspectable for demonstrations and future expert review.

The thresholds are **non-diagnostic project reference settings**. They produce only `normal`, `attention`, and `high_attention` tags. They must not be presented as a clinical conclusion, and should be reviewed by a qualified professional before any real-world deployment.

The sleep and activity education references are [CDC sleep guidance](https://www.cdc.gov/sleep/about/index.html) and [WHO physical-activity guidance](https://www.who.int/publications/i/item/9789240015128). The activity rule tracks weekly exercise days as a simple MVP habit indicator; it is not a replacement for duration- and intensity-based guidance.

## Test the local rule engine

```powershell
cd backend
pytest
```

## Test MaaS connectivity

With the server running and `GPUSTACK_API_KEY` set in the same terminal:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/llm/test" -ContentType "application/json" -Body '{"prompt":"请仅回复 CareAI API 已连接"}'
```

## Test the complete analysis flow

```powershell
$body = @{
  age = 21
  gender = "female"
  height_cm = 165
  weight_kg = 62
  systolic_bp = 118
  diastolic_bp = 76
  sleep_hours = 6.5
  exercise_days_per_week = 1
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/health/analyze" -ContentType "application/json" -Body $body
```

The endpoint returns a fixed JSON object:

```json
{
  "summary": "",
  "risk_level": "normal | attention | high_attention",
  "key_risks": [],
  "recommendations": [],
  "action_plan": [],
  "safety_notice": ""
}
```

`risk_level` and the source risk categories are always computed by local rules. The model is not permitted to add risks or make a disease diagnosis.

If no API key is configured, the LLM endpoints intentionally return HTTP 503. The local `/api/v1/health/risk-assessment` endpoint remains available for testing the rules without MaaS access.
