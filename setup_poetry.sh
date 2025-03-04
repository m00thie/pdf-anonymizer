#!/bin/bash
set -e

echo "Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -

echo "Creating Poetry environment..."
poetry install

echo "Creating lock file..."
poetry lock

echo "You can now remove requirements.txt as it's no longer needed"
echo "To build a wheel package, run: poetry build"
echo "To run the application: poetry run python -m pdf_anonymizer.app"
echo "To build and run with Docker: docker build -t pdf-anonymizer . && docker run -p 5000:5000 pdf-anonymizer"
