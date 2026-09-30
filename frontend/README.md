# Phase 7 Frontend

React + Vite frontend for the integrated clinical API.

## Run

Keep the FastAPI backend running on `http://127.0.0.1:8000`, then in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

Optional API override:

```powershell
$env:VITE_API_BASE="http://127.0.0.1:8000"
npm run dev
```
