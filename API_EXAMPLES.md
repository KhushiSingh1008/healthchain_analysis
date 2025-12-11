# API Usage Examples

This document provides various examples of how to use the HealthChain Analysis API.

## Table of Contents
1. [Using curl](#using-curl)
2. [Using Python](#using-python)
3. [Using Postman](#using-postman)
4. [Using JavaScript/Node.js](#using-javascriptnodejs)
5. [Response Examples](#response-examples)

---

## Using curl

### Basic Request (Windows PowerShell)
```powershell
curl -X POST "http://localhost:8000/analyze" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@C:\path\to\report.pdf"
```

### Basic Request (Windows CMD)
```cmd
curl -X POST "http://localhost:8000/analyze" ^
  -H "accept: application/json" ^
  -H "Content-Type: multipart/form-data" ^
  -F "file=@C:\path\to\report.pdf"
```

### Save Response to File
```powershell
curl -X POST "http://localhost:8000/analyze" `
  -F "file=@report.pdf" `
  -o analysis_result.json
```

### Health Check
```bash
curl http://localhost:8000/health
```

---

## Using Python

### Example 1: Basic Request
```python
import requests

# API endpoint
url = "http://localhost:8000/analyze"

# Open and send file
with open("medical_report.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

# Check response
if response.status_code == 200:
    result = response.json()
    print(f"Success! Found {len(result['extracted_data'])} test results")
    for test in result['extracted_data']:
        print(f"- {test['test_name']}: {test['value']} {test['unit']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

### Example 2: With Error Handling
```python
import requests
from pathlib import Path

def analyze_medical_report(file_path: str) -> dict:
    """Analyze a medical report and return results."""
    
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    url = "http://localhost:8000/analyze"
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f)}
            response = requests.post(url, files=files, timeout=120)
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.ConnectionError:
        raise Exception("Cannot connect to API. Is the service running?")
    except requests.exceptions.Timeout:
        raise Exception("Request timed out. File may be too large.")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"API error: {e.response.text}")

# Usage
try:
    result = analyze_medical_report("blood_test.pdf")
    print(f"Analysis complete: {result['message']}")
except Exception as e:
    print(f"Error: {e}")
```

### Example 3: Processing Multiple Files
```python
import requests
from pathlib import Path
import json

def batch_analyze(file_paths: list) -> dict:
    """Analyze multiple medical reports."""
    
    results = {}
    url = "http://localhost:8000/analyze"
    
    for file_path in file_paths:
        print(f"Processing: {file_path}")
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(url, files=files, timeout=120)
            
            if response.status_code == 200:
                results[file_path] = {
                    "status": "success",
                    "data": response.json()
                }
            else:
                results[file_path] = {
                    "status": "failed",
                    "error": response.text
                }
        
        except Exception as e:
            results[file_path] = {
                "status": "error",
                "error": str(e)
            }
    
    return results

# Usage
files = ["report1.pdf", "report2.jpg", "report3.pdf"]
results = batch_analyze(files)

# Save all results
with open("batch_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Example 4: Using the Test Client
```python
# Simply use the provided test client
import subprocess

result = subprocess.run(
    ["python", "test_client.py", "medical_report.pdf"],
    capture_output=True,
    text=True
)

print(result.stdout)
```

---

## Using Postman

### Setup
1. Open Postman
2. Create a new POST request
3. URL: `http://localhost:8000/analyze`
4. Go to "Body" tab
5. Select "form-data"
6. Add key: `file` (change type to "File")
7. Click "Select Files" and choose your PDF/image
8. Click "Send"

### Expected Response
Status: `200 OK`

Body:
```json
{
  "success": true,
  "message": "Successfully analyzed report. Found 3 test results.",
  "extracted_data": [...],
  "metadata": {...}
}
```

### Save as Collection
1. Click "Save" in Postman
2. Create collection: "HealthChain Analysis"
3. Add multiple requests for different files
4. Use Collection Runner for batch testing

---

## Using JavaScript/Node.js

### Example 1: Using Axios
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function analyzeMedicalReport(filePath) {
    const form = new FormData();
    form.append('file', fs.createReadStream(filePath));
    
    try {
        const response = await axios.post(
            'http://localhost:8000/analyze',
            form,
            {
                headers: form.getHeaders(),
                timeout: 120000 // 2 minutes
            }
        );
        
        console.log('Success!');
        console.log(`Found ${response.data.extracted_data.length} test results`);
        return response.data;
        
    } catch (error) {
        if (error.response) {
            console.error('API Error:', error.response.data);
        } else {
            console.error('Error:', error.message);
        }
        throw error;
    }
}

// Usage
analyzeMedicalReport('medical_report.pdf')
    .then(result => {
        console.log(JSON.stringify(result, null, 2));
    })
    .catch(err => {
        console.error('Failed:', err.message);
    });
```

### Example 2: Using Fetch API (Browser)
```javascript
async function uploadMedicalReport(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Analysis complete:', result);
        return result;
        
    } catch (error) {
        console.error('Upload failed:', error);
        throw error;
    }
}

// HTML usage
// <input type="file" id="fileInput" accept=".pdf,.jpg,.png">
// <button onclick="handleUpload()">Upload</button>

function handleUpload() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file');
        return;
    }
    
    uploadMedicalReport(file)
        .then(result => {
            displayResults(result);
        })
        .catch(error => {
            alert('Error: ' + error.message);
        });
}

function displayResults(result) {
    const tests = result.extracted_data;
    const html = tests.map(test => `
        <div class="test-result">
            <h3>${test.test_name || 'Unknown Test'}</h3>
            <p>Value: ${test.value || 'N/A'} ${test.unit || ''}</p>
            <p>Reference: ${test.reference_range || 'N/A'}</p>
            <p>Date: ${test.date || 'N/A'}</p>
        </div>
    `).join('');
    
    document.getElementById('results').innerHTML = html;
}
```

---

## Response Examples

### Successful Analysis
```json
{
  "success": true,
  "message": "Successfully analyzed report. Found 5 test results.",
  "ocr_text": "MEDICAL LABORATORY REPORT\nPatient Name: John Doe\nDate: 2023-11-15\n...",
  "extracted_data": [
    {
      "test_name": "Hemoglobin",
      "value": "14.5",
      "unit": "g/dL",
      "reference_range": "12.0-16.0",
      "date": "2023-11-15"
    },
    {
      "test_name": "White Blood Cell Count",
      "value": "7500",
      "unit": "cells/μL",
      "reference_range": "4000-11000",
      "date": "2023-11-15"
    },
    {
      "test_name": "Platelet Count",
      "value": "250000",
      "unit": "cells/μL",
      "reference_range": "150000-450000",
      "date": "2023-11-15"
    },
    {
      "test_name": "Blood Glucose",
      "value": "95",
      "unit": "mg/dL",
      "reference_range": "70-100",
      "date": "2023-11-15"
    },
    {
      "test_name": "Cholesterol Total",
      "value": "185",
      "unit": "mg/dL",
      "reference_range": "<200",
      "date": "2023-11-15"
    }
  ],
  "metadata": {
    "file_name": "blood_test_report.pdf",
    "file_type": ".pdf",
    "file_size": 245678,
    "ocr_text_length": 1234,
    "test_count": 5
  }
}
```

### No Tests Found
```json
{
  "success": true,
  "message": "No text could be extracted from the document",
  "ocr_text": "",
  "extracted_data": [],
  "metadata": {
    "file_type": ".pdf",
    "file_size": 12345
  }
}
```

### Error: Invalid File Type
```json
{
  "detail": "Invalid file type. Allowed types: .pdf, .png, .jpg, .jpeg, .bmp, .tiff, .tif"
}
```
Status: `400 Bad Request`

### Error: OCR Failed
```json
{
  "detail": "OCR processing failed: Failed to decode image"
}
```
Status: `500 Internal Server Error`

### Error: LLM Extraction Failed
```json
{
  "detail": "Data extraction failed: Failed to connect to Ollama: Connection refused"
}
```
Status: `500 Internal Server Error`

---

## Integration Examples

### Flask Application
```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
ANALYSIS_API = "http://localhost:8000/analyze"

@app.route('/upload', methods=['POST'])
def upload_report():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Forward to analysis API
    files = {'file': (file.filename, file.stream, file.content_type)}
    response = requests.post(ANALYSIS_API, files=files)
    
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(port=5000)
```

### Django View
```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests

@csrf_exempt
def analyze_report(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    
    # Send to analysis API
    files = {'file': (file.name, file.read(), file.content_type)}
    response = requests.post('http://localhost:8000/analyze', files=files)
    
    return JsonResponse(response.json(), status=response.status_code)
```

---

## Performance Tips

1. **Timeout**: Set appropriate timeouts (60-120s) for large PDFs
2. **File Size**: Compress large images before sending
3. **Batch Processing**: Process files sequentially, not in parallel (LLM is resource-intensive)
4. **Error Handling**: Always implement retry logic for network issues
5. **Caching**: Cache results for identical files using file hash

## Security Considerations

1. **File Validation**: Always validate file types on client side
2. **Size Limits**: Implement file size limits (e.g., max 10MB)
3. **Rate Limiting**: Add rate limiting for production use
4. **Authentication**: Add API key authentication for production
5. **HTTPS**: Use HTTPS in production environments
