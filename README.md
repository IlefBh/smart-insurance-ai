# سالمة

AI-powered smart insurance platform for inclusive micro-insurance.  
We combine classical ML (frequency & severity) with a DeepONet-based uncertainty module to support personalized product configuration, transparent pricing, and underwriting decisions.

## Hackathon Goal
Build a **credible, usable prototype** for the insurance/risk domain:
- A business pitch deck
- A functional technical solution (demo-ready)

## What the Prototype Does (MVP)
- Collects structured policyholder inputs (small business / micro-merchant profile)
- Produces an instant quote:
  - Risk assessment (probability + cost)
  - Product template selection + parameter tuning (capital / deductible / premium)
  - Transparent explanation (top factors + what-if simulation)
- Provides insurer portal features:
  - Underwriting review flag when uncertainty is high
  - Pricing breakdown and decision support

## AI Models
1. **Segmentation (optional)**: KMeans → `segment_id`
2. **Frequency**: Logistic Regression → `p_claim = P(claim)`
3. **Severity**: GammaRegressor → `expected_cost = E(cost | claim)`
4. **Uncertainty (Deep Learning)**: DeepONet → scenario curve + `p50/p90` (stress testing)

## Tech Stack
- **Backend**: FastAPI + Uvicorn
- **Frontend**: Streamlit (rapid demo)
- **AI**: scikit-learn + PyTorch (DeepONet)
- **DB**: SQLite (hackathon default)

## Repository Structure (high-level)
- `src/api/` : FastAPI endpoints
- `src/app/` : Streamlit UI (policyholder + insurer)
- `src/models/` : ML models + DeepONet
- `src/pricing/` : product templates + pricing engine
- `src/explain/` : transparency (drivers + what-if)
- `scripts/` : training utilities
- `artifacts/` : saved models (ignored by git)
- `data/` : datasets (ignored by git)

## Quickstart (Local)

### 1) Create a virtual environment
```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate
