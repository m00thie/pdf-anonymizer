FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==2.1.1

# Configure poetry to not use a virtual environment in the container
RUN poetry config virtualenvs.create false

# Copy application code
COPY . .

# Install dependencies
RUN poetry install

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "-m", "pdf_anonymizer.app"]
