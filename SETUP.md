# Setup Guide - HealthChain Analysis Microservice

## Quick Start (Windows)

### 1. Prerequisites Installation

#### Install Python 3.9+
Download from: https://www.python.org/downloads/
- During installation, check "Add Python to PATH"

#### Install Ollama
1. Download from: https://ollama.ai/download
2. Install and run Ollama
3. Pull Llama 3.2 model:
   ```bash
   ollama pull llama3.2
   ```
4. Start Ollama server:
   ```bash
   ollama serve
   ```

#### Install Poppler (for PDF support)
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract to a location (e.g., `C:\Program Files\poppler`)
3. Add the `bin` folder to your system PATH:
   - Right-click "This PC" → Properties → Advanced system settings
   - Click "Environment Variables"
   - Under "System variables", find "Path" and click "Edit"
   - Click "New" and add: `C:\Program Files\poppler\Library\bin`
   - Click OK on all dialogs

### 2. Project Setup

#### Step 1: Navigate to Project Directory
```bash
cd c:\Users\Khushi\OneDrive\Desktop\healthchain_analysis
```

#### Step 2: Create Virtual Environment
```bash
python -m venv venv
```

#### Step 3: Activate Virtual Environment
```bash
.\venv\Scripts\activate
```

You should see `(venv)` at the start of your command prompt.

#### Step 4: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- FastAPI & Uvicorn (web framework)
- PaddleOCR & PaddlePaddle (OCR engine)
- pdf2image (PDF processing)
- OpenCV & Pillow (image processing)
- And other dependencies

**Note**: First installation may take 5-10 minutes as PaddlePaddle is large.

#### Step 5: Verify Setup
```bash
python verify_setup.py
```

This script checks:
- Python version
- All required packages
- Ollama connection
- Llama 3.2 model availability
- Project file structure

### 3. Running the Service

#### Option A: Using the Start Script (Easiest)
```bash
start.bat
```

#### Option B: Manual Start
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Start the service
python -m app.main
```

#### Option C: Using Uvicorn Directly
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The service will start on: **http://localhost:8000**

### 4. Testing the Service

#### Check Service Health
Open browser and visit: http://localhost:8000/health

Or use curl:
```bash
curl http://localhost:8000/health
```

#### View API Documentation
Interactive docs: http://localhost:8000/docs

Alternative docs: http://localhost:8000/redoc

#### Test with Sample File
```bash
# Activate virtual environment first
.\venv\Scripts\activate

# Run test client
python test_client.py path\to\your\medical_report.pdf
```

#### Manual API Test with curl
```bash
curl -X POST "http://localhost:8000/analyze" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:\path\to\medical_report.pdf"
```

### 5. Expected Output

When you send a medical report, you'll get a JSON response like:

```json
{
  "success": true,
  "message": "Successfully analyzed report. Found 5 test results.",
  "ocr_text": "Patient Name: John Doe\nDate: 2023-11-15\n...",
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
    "file_name": "report.pdf",
    "file_type": ".pdf",
    "file_size": 245678,
    "ocr_text_length": 1234,
    "test_count": 5
  }
}
```

## Troubleshooting

### Issue: "Cannot connect to Ollama"
**Solution**: 
1. Ensure Ollama is running: `ollama serve`
2. Check if it's accessible: `curl http://localhost:11434/api/tags`
3. Verify Llama 3.2 is installed: `ollama list`

### Issue: "PDF processing failed"
**Solution**:
1. Verify Poppler is installed and in PATH
2. Test: `pdftoppm -v` should show version info
3. Restart terminal after adding to PATH

### Issue: "PaddleOCR initialization failed"
**Solution**:
1. PaddleOCR downloads models on first run - ensure internet connection
2. Models are cached in `~/.paddleocr/`
3. On slow connections, first run may take several minutes

### Issue: "ModuleNotFoundError"
**Solution**:
1. Ensure virtual environment is activated
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check Python version: `python --version` (should be 3.9+)

### Issue: "Port 8000 already in use"
**Solution**:
1. Change port in `app/main.py` (last line)
2. Or kill process using port: `netstat -ano | findstr :8000`

### Issue: "OCR returns empty text"
**Solution**:
1. Check if image/PDF is clear and readable
2. Ensure file is not corrupted
3. Try increasing DPI in `app/services/ocr.py` (line 82)

## Development Tips

### Enable GPU Acceleration (if CUDA available)
In `app/services/ocr.py`, line 27:
```python
use_gpu=True  # Change from False to True
```

### Adjust LLM Temperature
In `app/services/llm.py`, modify temperature parameter:
```python
self._call_ollama(prompt, temperature=0.1)  # Lower = more consistent
```

### Change Ollama Model
In `app/services/llm.py`, line 20:
```python
def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2"):
```

### Modify Extraction Prompts
Edit prompts in `app/utils/prompts.py`

### Increase Timeout for Large Files
In `app/services/llm.py`, line 99:
```python
timeout=60  # Increase if processing large documents
```

## Next Steps

1. **Customize Prompts**: Modify `app/utils/prompts.py` for your specific medical report format
2. **Add Authentication**: Implement API key validation in `app/main.py`
3. **Database Integration**: Store results in a database
4. **Batch Processing**: Add endpoint for multiple files
5. **Docker Deployment**: Create Dockerfile for containerization

## Support

For issues or questions:
1. Check logs in the terminal
2. Review API documentation at http://localhost:8000/docs
3. Run verification script: `python verify_setup.py`

## Resources

- FastAPI Docs: https://fastapi.tiangolo.com/
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- Ollama: https://ollama.ai/
- Llama Models: https://ai.meta.com/llama/
