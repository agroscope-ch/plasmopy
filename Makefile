.PHONY: tests docs

install:
	@echo "Installing dependencies..."
	poetry install --no-root
	poetry run pre-commit install

activate:
	@echo "Activating virtual environment..."
	poetry env activate

setup: install activate

docs:
	@echo "Save documentation to docs... "
	poetry run pdoc src -o docs --html --force
	#@echo "View API documentation..."
	#poetry run pdoc src/*.py --http localhost:8080

tests:
	pytest

run:
	poetry run python3 src/main.py
	
app:
	poetry run streamlit run plasmopy-app.py --server.enableCORS=false
