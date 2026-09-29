.PHONY: install profile analyze test app api run all clean

install:
	pip install -r requirements.txt

profile:      ## Step 1: load, profile, coverage + data-quality report
	python scripts/run_profile.py

analyze:      ## Step 2: analysis, CV, fit model, figures
	python scripts/run_analysis.py
	python scripts/compare_models.py

insights:     ## run the Insight Discovery Engine (discover -> challenge -> save)
	python scripts/run_insights.py

test:
	python -m pytest tests/ -q

app:          ## launch the Streamlit dashboard
	streamlit run app/app.py

api:          ## launch the interoperability API
	uvicorn api.main:app --reload --port 8000

run: profile analyze app   ## one command: rebuild everything then open the app

all: install profile analyze test

clean:
	rm -rf outputs/figures/*.png outputs/*.json outputs/*.csv outputs/model.joblib
