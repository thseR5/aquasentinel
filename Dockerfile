FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; scientific wheels are prebuilt.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Regenerate every output at image build time so the app starts ready.
RUN python scripts/run_profile.py && python scripts/run_analysis.py && python scripts/compare_models.py && python scripts/run_insights.py

EXPOSE 8501
# python:slim has no curl, so the health check uses Python's standard library.
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
