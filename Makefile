.PHONY: install ingest validate transform analytics run

install:
	python -m pip install -r requirements.txt

ingest:
	@echo "Ingestion will be implemented in a later phase."

validate:
	@echo "Validation will be implemented in a later phase."

transform:
	@echo "dbt transformations will be implemented in a later phase."

analytics:
	@echo "Analytics will be implemented in a later phase."

run:
	@echo "The end-to-end pipeline will be implemented in a later phase."
