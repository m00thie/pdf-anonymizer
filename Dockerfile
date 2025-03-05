FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==2.1.1

# Configure poetry to not use a virtual environment in the container
RUN poetry config virtualenvs.create false

# Copy application code
COPY . .

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Expose the port the app runs on
EXPOSE 5000

# Set environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Command to run the application with waitress
CMD ["python", "-m", "pdf_anonymizer.app"]
