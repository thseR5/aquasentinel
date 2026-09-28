# Deploying AquaSentinel (live demo URL)

The dashboard deploys free on **Streamlit Community Cloud**. It pulls the app
directly from a public GitHub repo, so the repo must be on GitHub first.

Everything in this repo is already deploy-ready:
- `requirements.txt` at the root (no heavy/fragile deps — `shap` removed).
- `app/app.py` as the entry point (imports resolve via `src/` automatically).
- `outputs/model.joblib` is committed (38 KB) so the app loads instantly; if the
  cloud ever installs an incompatible scikit-learn, the app **rebuilds the model
  on first load** by itself (~10 s, cached), so it never breaks.
- `.streamlit/config.toml` (theme + headless server) and `runtime.txt` (Python 3.12).

## Step 1 — put the repo on GitHub (one-time)
```bash
cd ~/Desktop/aquasentinel
gh repo create aquasentinel --public --source=. --remote=origin --push
# or, without gh: create an empty public repo on github.com, then:
#   git remote add origin https://github.com/<you>/aquasentinel.git
#   git push -u origin main
```

## Step 2 — deploy on Streamlit Community Cloud
1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `<you>/aquasentinel`
   - **Branch:** `main`
   - **Main file path:** `app/app.py`
4. Open **Advanced settings** → set **Python version = 3.12**.
5. Click **Deploy**. First build takes ~2–4 minutes.

You'll get a public URL like `https://<name>.streamlit.app` — put it in the Devpost
submission and open it in the demo video.

## Step 3 — deploy the API too (optional, for the interoperability demo)
The FastAPI service (`api/main.py`) can go on **Render** (free web service):
- Build: `pip install -r requirements.txt`
- Start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
Then `<render-url>/docs` shows the SensorThings/GeoJSON/FHIR endpoints live.

## Alternatives
- **Hugging Face Spaces** (Streamlit SDK): create a Space, push this repo, set the
  app file to `app/app.py`.
- **Local for judges:** `pip install -r requirements.txt && streamlit run app/app.py`.

## Troubleshooting
- Blank map: Streamlit Cloud needs outbound internet for map tiles — it has it by
  default.
- Slow first load: that's the one-time model rebuild fallback; it's cached after.
- Import errors: confirm **Main file path** is `app/app.py`, not `app.py`.
