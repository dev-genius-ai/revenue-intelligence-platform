.PHONY: install ingest validate transform analytics run

install:
	python -m pip install -r requirements.txt

ingest:
	python ingestion/load_raw.py

validate:
	python ingestion/validate.py

transform:
	@echo "dbt transformations will be implemented in a later phase."

analytics:
	@echo "Analytics will be implemented in a later phase."

run:
	@echo "The end-to-end pipeline will be implemented in a later phase."
