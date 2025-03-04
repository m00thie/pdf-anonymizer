# PDF Anonymizer

A service for anonymizing sensitive content in PDF files.

## Features

- Anonymize sensitive content in PDF files
- Support for multiple output formats (PDF, Image, Markdown)
- Flexible delivery options (direct response or URL)

## Installation

### Using Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

### Using Docker

```bash
# Build the Docker image
docker build -t pdf-anonymizer .

# Run the container
docker run -p 5000:5000 pdf-anonymizer
```

## Usage

### API Endpoint

`POST /api/pdf/anonymize`

#### Request Body

```json
{
  "sensitive_content": ["word1", "word2"],
  "pdf_content": "base64_encoded_pdf_content",
  "pdf_file": "url_to_pdf_file",
  "output_format": ["pdf", "img", "md"],
  "result_deliver": "response"
}
```

- `sensitive_content`: List of words to be anonymized (required)
- `pdf_content`: Base64 encoded PDF file (either this or pdf_file is required)
- `pdf_file`: URL to PDF file (either this or pdf_content is required)
- `output_format`: List of output formats (optional, default: ["pdf"])
- `result_deliver`: Delivery method (optional, default: "response")

#### Response

```json
{
  "pdf": "base64_encoded_anonymized_pdf",
  "img": ["base64_encoded_image_page_1", "base64_encoded_image_page_2"],
  "md": "markdown_content"
}
```

## Development

```bash
# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Build wheel package
poetry build
```

## License

[License information]
