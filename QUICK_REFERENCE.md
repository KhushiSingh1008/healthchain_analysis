# Quick Reference Card - HealthChain Analysis

## 🚀 Quick Start (3 Commands)

```powershell
# 1. Create & activate virtual environment
python -m venv venv; .\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start service
python -m app.main
```

**Service URL**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs

---

## 📋 Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Ollama installed and running (`ollama serve`)
- [ ] Llama 3.2 model pulled (`ollama pull llama3.2`)
- [ ] Poppler installed (for PDF support)
- [ ] Virtual environment created

---

## 🔧 Common Commands

### Setup
```powershell
# Verify setup
python verify_setup.py

# Run startup script (Windows)
start.bat
```

### Testing
```powershell
# Test with sample file
python test_client.py report.pdf

# Health check
curl http://localhost:8000/health

# API test
curl -X POST http://localhost:8000/analyze -F "file=@report.pdf"
```

### Development
```powershell
# Run with auto-reload
uvicorn app.main:app --reload

# Check Ollama models
ollama list

# Test Ollama connection
curl http://localhost:11434/api/tags
```

---

## 📁 File Structure (Quick View)

```
healthchain_analysis/
├── app/
│   ├── main.py           # FastAPI app
│   ├── services/
│   │   ├── ocr.py        # PaddleOCR
│   │   └── llm.py        # Ollama
│   └── utils/
│       └── prompts.py    # LLM prompts
├── requirements.txt      # Dependencies
├── start.bat            # Startup script
├── verify_setup.py      # Setup checker
└── test_client.py       # API tester
```

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/analyze` | POST | Analyze report |
| `/docs` | GET | API documentation |

---

## 📤 Request Format

```bash
POST /analyze
Content-Type: multipart/form-data
file: <PDF or Image>
```

**Supported Formats**: .pdf, .png, .jpg, .jpeg, .bmp, .tiff

---

## 📥 Response Format

```json
{
  "success": true,
  "message": "Found 5 test results",
  "ocr_text": "...",
  "extracted_data": [
    {
      "test_name": "Hemoglobin",
      "value": "14.5",
      "unit": "g/dL",
      "reference_range": "12.0-16.0",
      "date": "2023-11-15"
    }
  ],
  "metadata": {...}
}
```

---

## 🔥 Troubleshooting Quick Fixes

### "Cannot connect to Ollama"
```powershell
ollama serve
```

### "PDF processing failed"
- Install Poppler
- Add to PATH: `C:\Program Files\poppler\Library\bin`

### "Module not found"
```powershell
.\venv\Scripts\activate
pip install -r requirements.txt
```

### "Port 8000 in use"
```python
# Change in app/main.py (last line)
uvicorn.run("app.main:app", port=8001)
```

### "OCR too slow"
```python
# Enable GPU in app/services/ocr.py
use_gpu=True  # Line 27
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
PORT=8000
LOG_LEVEL=INFO
```

### Key Parameters

| Setting | File | Line | Default |
|---------|------|------|---------|
| Ollama URL | llm.py | 20 | localhost:11434 |
| Model | llm.py | 20 | llama3.2 |
| Max Retries | llm.py | 25 | 3 |
| Temperature | llm.py | 99 | 0.1 |
| PDF DPI | ocr.py | 82 | 300 |
| Use GPU | ocr.py | 27 | False |
| Timeout | llm.py | 99 | 60s |

---

## 📊 Performance Metrics

| Operation | Typical Time |
|-----------|-------------|
| Single Image OCR | 2-5 sec |
| 5-page PDF OCR | 10-30 sec |
| LLM Extraction | 5-15 sec |
| Full Pipeline | 10-45 sec |

---

## 🐛 Debug Mode

```python
# In app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📚 Documentation Files

- **README.md** - Overview & quick start
- **SETUP.md** - Detailed setup guide
- **API_EXAMPLES.md** - Usage examples
- **PROJECT_STRUCTURE.md** - Complete structure
- **QUICK_REFERENCE.md** - This file

---

## 🔗 Useful URLs

- **Service**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Ollama**: http://localhost:11434

---

## 💡 Tips

1. **First Run**: Takes longer (downloads OCR models)
2. **GPU**: 3-5x faster if CUDA available
3. **Quality**: Higher DPI = better OCR = slower
4. **Accuracy**: Lower temperature = more consistent
5. **Debugging**: Check logs in terminal

---

## 🆘 Getting Help

1. Run: `python verify_setup.py`
2. Check logs in terminal
3. Test health: `curl localhost:8000/health`
4. Review docs: http://localhost:8000/docs

---

**Version**: 1.0.0  
**Updated**: December 11, 2025
