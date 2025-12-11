# HealthChain Analysis Microservice

A standalone microservice for OCR and extraction of medical report data using PaddleOCR and Llama 3.2 via Ollama.

## Features

- **OCR Processing**: Extract text from medical reports (PDF and Images)
- **LLM-based Extraction**: Extract structured medical test data using Llama 3.2
- **RESTful API**: Simple FastAPI endpoint for analysis
- **Error Handling**: Comprehensive error handling with retries
- **JSON Validation**: Strict JSON output validation with fallback mechanisms

## Tech Stack

- **Language**: Python 3.9+
- **Framework**: FastAPI
- **OCR Engine**: PaddleOCR
- **LLM**: Llama 3.2 via Ollama (localhost:11434)
- **PDF Processing**: pdf2image

## Project Structure

```
healthchain_analysis/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr.py           # PaddleOCR service
│   │   └── llm.py           # Ollama LLM service
│   └── utils/
│       ├── __init__.py
│       └── prompts.py       # LLM prompts for extraction
└── requirements.txt
```

## Prerequisites

1. **Python 3.9+** installed
2. **Ollama** installed and running with Llama 3.2 model
3. **Poppler** (for PDF processing) - Required by pdf2image
   - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/
   - Add to PATH or set POPPLER_PATH environment variable

## Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd c:\Users\Khushi\OneDrive\Desktop\healthchain_analysis
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Ensure Ollama is running** with Llama 3.2:
   ```bash
   ollama pull llama3.2
   ollama serve
   ```

## Running the Service

### Development Mode

```bash
python -m app.main
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at: `http://localhost:8000`

## API Documentation

Once running, access:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## Usage

### Endpoint: POST /analyze

Accepts a medical report file (PDF or Image) and returns extracted test results.

**Example using curl**:

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/medical_report.pdf"
```

**Example using Python**:

```python
import requests

url = "http://localhost:8000/analyze"
files = {"file": open("medical_report.pdf", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

**Response Format**:

```json
{
  "success": true,
  "message": "Successfully analyzed report. Found 5 test results.",
  "ocr_text": "Extracted text from the report...",
  "extracted_data": [
    {
      "test_name": "Hemoglobin",
      "value": "14.5",
      "unit": "g/dL",
      "reference_range": "12.0-16.0",
      "date": "2023-11-15"
    }
  ],
  "metadata": {
    "file_name": "medical_report.pdf",
    "file_type": ".pdf",
    "file_size": 245678,
    "ocr_text_length": 1234,
    "test_count": 5
  }
}
```

## Supported File Types

- **Images**: .png, .jpg, .jpeg, .bmp, .tiff, .tif
- **Documents**: .pdf

## Error Handling

The service includes comprehensive error handling:

- **400 Bad Request**: Invalid file type or empty file
- **500 Internal Server Error**: OCR failure, LLM extraction failure, or Ollama connection issues

The LLM extraction includes a retry mechanism (3 attempts) with fallback prompts.

## Configuration

You can customize the service by modifying:

- **Ollama URL**: Default is `http://localhost:11434`
- **Model**: Default is `llama3.2`
- **Max Retries**: Default is 3

Edit these in `app/services/llm.py`:

```python
llm_service = LLMService(
    ollama_url="http://localhost:11434",
    model="llama3.2"
)
```

## Logging

The service uses Python's logging module. Logs include:
- OCR processing status
- LLM extraction attempts
- Error details with stack traces

## Troubleshooting

### Ollama Connection Error

Ensure Ollama is running:
```bash
ollama serve
```

### PDF Processing Error

Install Poppler and add to PATH or set environment variable.

### OCR Initialization Error

PaddleOCR will download models on first run. Ensure internet connectivity.

## Future Enhancements

- Docker containerization
- Database integration for storing results
- Batch processing endpoint
- Authentication/API keys
- Support for more medical report formats

## License

MIT

## Author

HealthChain Analysis Team
