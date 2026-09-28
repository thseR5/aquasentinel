FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; scientific wheels are prebuilt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build model artifact at image build time so the app starts ready.
RUN python scripts/run_profile.py && python scripts/run_analysis.py || true

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
