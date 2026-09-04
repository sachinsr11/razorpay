# AGENTS.md

## Project

Reclaim — Agent for B2B receivables recovery. Detects revenue at risk,
diagnoses root cause, selects an intervention, and executes a bounded recovery
workflow with compliant escalation, stopping rules, and a full audit trail.
The demo metric is **money recovered across a batch**, not just detection.

Stack: Python 3.11+, FastAPI (`app/main.py`), Streamlit dashboard
(`app/streamlit_app.py`), pytest. All customer responses and email sends are
**simulated** — never wire real email/SMS.

## Commands

```powershell
py -3.12 -m venv .venv                 # create the project environment
.venv\Scripts\Activate.ps1            # activate it in PowerShell
python -m pip install -r requirements.txt
uvicorn app.main:app --reload          # API server
streamlit run app/streamlit_app.py     # dashboard
python -m pytest tests/ -x -q          # all tests
python -m pytest tests/test_compliance.py -q
```

All dependency installation and test commands must run through the project
`.venv`; do not use the system Python environment for testing.

`OPENCODE_ZEN_API_KEY` must be set in `.env` (see `.env.example`) before any
LLM call works; engine rules/tests run fine without it.

## Pipeline (per invoice)

detect → diagnose → select intervention → compliance check → execute (simulated)
→ audit log. Orchestrated by `app/engine/executor.py`. Every decision must land
in the audit trail via `app/engine/auditor.py`: timestamp, action, reason, LLM
reasoning, compliance result.

## Escalation ladder — email only, exactly 3 rungs

| Rung | Trigger | Action |
|------|---------|--------|
| 1 | Day 1–7 overdue | Gentle reminder email |
| 2 | Day 8–30 **or** diagnosis = cash-flow-strapped | Firm reminder + payment plan offer |
| 3 (terminal) | Day 30+ AND amount > $10K, **or** 2 failed automated attempts | Generate AR-rep brief, freeze automation |

Do NOT add phone, SMS, legal-referral tiers, or extra aging buckets. Rung 3 is
the hard cap on automation.

## Diagnosis categories → fixed actions (`app/models/enums.py`, `app/engine/diagnoser.py`)

- `forgetful` → rung 1 gentle email
- `cash_flow_strapped` → force rung 2 (firm + payment plan)
- `disputed` → **immediate freeze** to `FROZEN_HUMAN_REVIEW`, no automation
- `wrong_bounced_contact` → **immediate freeze**, same as disputed

These four are final. Do not reintroduce "dissatisfied" or other categories.
Detection is aging bucket + eligibility check only — no risk scoring, no
industry patterns.

## Compliance constants — single source of truth in `app/engine/compliance.py`

```python
MAX_AUTOMATED_TOUCHES = 3
COOLDOWN_DAYS = 4
HIGH_VALUE_THRESHOLD = 10_000      # USD
MAX_FAILED_ATTEMPTS_BEFORE_HANDOFF = 2
BUSINESS_HOURS_START = 9           # 9 AM
BUSINESS_HOURS_END = 18            # 6 PM
MAX_CASE_AGE_DAYS = 90
```

Engine code must import these constants, never re-hardcode numbers inline.
Eligibility = OVERDUE status, not frozen, touches < cap, cooldown elapsed,
not already at rung 3.

## Promise-to-Pay (`app/engine/promise_to_pay.py`)

Customer promise (date + amount) → log it, set `status = PROMISE_TO_PAY`
(automation frozen). On promised date: fulfilled → mark PAID, record recovery;
missed → log breach, increment broken-promises counter (counts toward failed
attempts), re-enter workflow at rung 2.

## LLM client (`app/llm/client.py`)

- Model: `gpt-5.6-luna` (OpenCode Go)
- Endpoint: base_url `https://opencode.ai/zen/go/v1`, Responses API
  (`https://opencode.ai/zen/go/v1/responses`) via the `openai` Python SDK
  — note `/go/` in the path; plain `https://opencode.ai/zen/v1` is a
  different product and will 404/fail auth for Go keys
- Key env var: `OPENCODE_ZEN_API_KEY`
- Used only for: diagnosis classification, email drafting, handoff brief.
  Rung selection and eligibility are deterministic code, not LLM.

## Seed data (`app/data/seed.py`) — ~120 synthetic invoices

Aging buckets: ~35 in 1–7d, ~35 in 8–30d, ~50 in 30+ (internal spread 31–90d;
no explicit sub-buckets). Mix of amount tiers so recovery-by-category breakdowns
have volume. Some invoices ship with pre-baked promise-to-pay / dispute /
bounced-contact states.

## Scope guards for this hackathon build

- Batch size target: 100–150 invoices (~120) so per-category metrics are meaningful.
- Dashboard must surface: $ at risk, $ recovered, recovery rate, cases resolved,
  stopping rules triggered, per-case audit trail with reasoning.
- No real outbound communications, ever — simulation only, even if asked mid-demo.

## Development Approach

This is a beginner-friendly hackathon project. Implement incrementally:

  - Create the complete folder structure first.
  - Explain the purpose of each component.
  - Implement one pipeline stage at a time, starting with models and synthetic data.
  - After each stage, run the relevant tests and verify the implementation works.
  - Keep the implementation simple and understandable.
  - Avoid unnecessary abstractions and production-grade complexity.
  - Do not expand the agreed project scope without explicit approval.
