.PHONY: help install api ui train test format lint clean

help:
	@echo "Targets:"
	@echo "  install  - Install dependencies"
	@echo "  api      - Run FastAPI locally"
	@echo "  ui       - Run Streamlit UI"
	@echo "  train    - Train all models (1-2-3 + DeepONet optional)"
	@echo "  test     - Run tests"
	@echo "  format   - Format code (black)"
	@echo "  lint     - Lint code (ruff)"
	@echo "  clean    - Remove caches"

install:
	pip install -U pip
	pip install -e .

api:
	uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

ui:
	streamlit run src/app/streamlit_app.py

train:
	python scripts/train_all.py

test:
	pytest -q

format:
	black src tests scripts

lint:
	ruff check src tests scripts

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__
