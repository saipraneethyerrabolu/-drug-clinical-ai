# Drug Clinical AI — Phase 9

Phase 9 keeps the integrated Phase 1–8 workflow and adds an official FDA drug-label reference fallback for medicines that do not have a matching local dosage rule.

## What changed

- DDI UI keeps **DDI Assessment: No Known Interaction Detected** when no known interaction is found in the configured data.
- Missing local dosage information triggers `GET /api/dosage/official-label?medicine_name=...`.
- The backend queries the official openFDA drug-label API and returns label metadata: indication, route, dosage form/strength, source, and whether an official Dosage & Administration section exists.
- The application intentionally does not reproduce actionable dosing instructions from the external label. It indicates that the official prescribing information contains the dosing section for clinician review.

## Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Then open `http://127.0.0.1:5173`.

The computer running the backend needs internet access for the openFDA fallback. If openFDA is unavailable or no matching label is found, the frontend shows the corresponding reference lookup status instead of inventing data.
