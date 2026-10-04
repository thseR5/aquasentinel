# Deploying AquaSentinel (live demo URL)

The dashboard deploys free on **Streamlit Community Cloud**. It pulls the app
directly from a public GitHub repo, so the repo must be on GitHub first.

Everything in this repo is already deploy-ready:
- `requirements.txt` at the root (no heavy or fragile dependencies).
- `app/app.py` as the entry point (imports resolve via `src/` automatically).
- `outputs/model.joblib` is committed (38 KB) so the app loads instantly; if the
  cloud ever installs an incompatible scikit-learn, the app **rebuilds the model
  on first load** by itself (~10 s, cached), so it never breaks.
- `.streamlit/config.toml` (theme + headless server) and `runtime.txt` (Python 3.12).

## Step 1 — put the repo on GitHub (one-time)
```bash
cd ~/Desktop/aquasentinel2   # the submission folder
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
Then `<render-url>/docs` shows the SensorThings, GeoJSON, FHIR and `/insights` endpoints live.

## Alternatives
- **Hugging Face Spaces** (Streamlit SDK): create a Space, push this repo, set the
  app file to `app/app.py`.
- **Local for judges:** `pip install -r requirements.txt && streamlit run app/app.py`.

## Troubleshooting
- Blank map: the map loads its JavaScript and tiles from the internet. Streamlit Cloud
  has outbound access by default; on a restricted network the map stays empty while the
  rest of the app works.
- Slow first load (about 10 to 20 seconds): the insight engine runs its resampling
  tests once, then the result is cached for every visitor.
- Import errors: confirm **Main file path** is `app/app.py`, not `app.py`.
