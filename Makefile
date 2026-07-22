.PHONY: install ingest validate transform analytics forecast anomaly dashboard run

install:
	python -m pip install -r requirements.txt

ingest:
	python ingestion/load_raw.py

validate:
	python ingestion/validate.py

transform:
	cd dbt_project && dbt run --profiles-dir .

analytics:
	cd dbt_project && dbt run --select path:models/analytics --profiles-dir .

forecast:
	python forecasting/run_forecast.py

anomaly:
	python anomaly_detection/run_anomaly_detection.py

dashboard:
	streamlit run streamlit_app/app.py

run:
	python ingestion/load_raw.py
	python ingestion/validate.py
	cd dbt_project && dbt run --profiles-dir .
	python forecasting/run_forecast.py
	python anomaly_detection/run_anomaly_detection.py
