"""
Vision-based LLM service for analyzing medical reports using Llama 3.2 Vision.
Supports multi-page PDFs, automatic report type segregation, and ROBUST JSON cleaning.
"""
import base64
import io
import json
import logging
import re
from typing import Any, Dict, List

# Try importing ollama
try:
    import ollama
except ImportError:
    ollama = None

# Try importing PDF processing libraries
try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logger = logging.getLogger(__name__)
    logger.warning("pdf2image not installed - PDF processing disabled")

logger = logging.getLogger(__name__)

# --- PROMPT ---
VISION_PROMPT = """You are a medical data assistant. Analyze this image.

STEP 1: HEADER
- Extract Patient Name and Date.

STEP 2: TEST EXTRACTION
- Extract all tests.

CRITICAL FORMATTING RULES (DO NOT IGNORE):
1. NO COMMAS IN NUMBERS: Write 5100, NOT 5,100. (Remove all thousands separators).
2. ALL VALUES MUST HAVE KEYS: Never write a standalone 'null'. It must be "reference_range": null.
3. NO TRAILING COMMAS: Do not put a comma after the last item.
4. JSON ONLY: No markdown, no comments.

Required JSON Structure:
{
  "report_type": "string",
  "patient_name": "string or null",
  "report_date": "string or null",
  "tests": [
    {
      "test_name": "string",
      "value": "number or string (NO COMMAS)",
      "unit": "string",
      "reference_range": "string or null",
      "status": "string or null"
    }
  ]
}
"""

def _extract_json_from_response(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from model response.
    Includes a "NUCLEAR" CLEANER to fix trailing commas, comments, and markdown.
    """
    try:
        # 1. Remove Markdown Code Blocks (```json ... ```)
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # 2. Isolate the JSON block
        start_index = text.find('{')
        end_index = text.rfind('}')
        
        if start_index != -1 and end_index != -1:
            text = text[start_index : end_index + 1]

        # 3. Remove Comments (// ... or # ...)
        text = re.sub(r'//.*', '', text) 
        text = re.sub(r'#.*', '', text)

        # 4. FIX TRAILING COMMAS (The most common error)
        # Replaces ", }" with "}" and ", ]" with "]"
        text = re.sub(r',\s*([\]}])', r'\1', text)

        return json.loads(text)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing Failed. Raw text:\n{text}")
        # Return a partial error object instead of crashing
        return {
            "report_type": "Error",
            "patient_name": None,
            "error": "JSON Parsing Failed",
            "raw_text": text[:100], # Send snippet for debugging
            "tests": []
        }

def analyze_medical_image(file_bytes: bytes, model: str = "llama3.2-vision") -> Dict[str, Any]:
    """
    Analyze a single image using Llama 3.2 Vision model.
    """
    if ollama is None:
        raise Exception("ollama package not installed. Run: pip install ollama")
    
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Empty file provided")
    
    try:
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        logger.info(f"Calling Ollama vision model: {model}")
        
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': VISION_PROMPT, 'images': [base64_image]}],
            options={'temperature': 0}
        )
        
        if not response or 'message' not in response:
            raise ValueError("Invalid response from Ollama")
        
        response_text = response['message']['content']
        return _extract_json_from_response(response_text)
        
    except Exception as e:
        logger.error(f"Error during vision analysis: {str(e)}")
        raise Exception(f"Vision analysis failed: {str(e)}")

# --- PDF HELPERS ---

def _is_pdf(file_bytes: bytes) -> bool:
    return file_bytes[:4] == b'%PDF'

def _convert_pdf_to_images(file_bytes: bytes) -> List[bytes]:
    if not PDF_SUPPORT:
        raise Exception("PDF processing not available. Install: pip install pdf2image Pillow")
    try:
        # Convert PDF pages to PIL images
        images = convert_from_bytes(file_bytes, fmt='png', dpi=200)
        image_bytes_list = []
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_bytes_list.append(img_byte_arr.getvalue())
        return image_bytes_list
    except Exception as e:
        logger.error(f"Failed to convert PDF: {str(e)}")
        raise Exception(f"PDF conversion failed: {str(e)}")

def _segregate_reports_by_type(page_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups pages by report type and merges them.
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for page in page_results:
        # If the page failed, group it under "Error"
        if 'error' in page:
            grouped[f"error_{page.get('page_number')}"].append(page)
        else:
            # Handle cases where report_type might be messy
            rtype = page.get('report_type', 'Unknown')
            if not isinstance(rtype, str): rtype = 'Unknown'
            grouped[rtype].append(page)
    
    merged_reports = []
    for rtype, pages in grouped.items():
        if rtype.startswith('error_'):
            merged_reports.extend(pages)
            continue
            
        merged = {
            'report_type': rtype,
            # Find the first non-null patient name in the group
            'patient_name': next((p.get('patient_name') for p in pages if p.get('patient_name')), None),
            'report_date': next((p.get('report_date') for p in pages if p.get('report_date')), None),
            'tests': [],
            'page_numbers': []
        }
        
        for p in pages:
            merged['tests'].extend(p.get('tests', []))
            if 'page_number' in p:
                merged['page_numbers'].append(p['page_number'])
                
        merged_reports.append(merged)
        
    return merged_reports

# --- MAIN EXPORTED FUNCTION ---

def analyze_medical_document(file_bytes: bytes, model: str = "llama3.2-vision") -> List[Dict[str, Any]]:
    """
    Analyze a document (PDF or Image) and return a list of segregated reports.
    """
    if not file_bytes:
        raise ValueError("Empty file")

    is_pdf = _is_pdf(file_bytes)
    
    if is_pdf:
        logger.info("Processing PDF...")
        page_images = _convert_pdf_to_images(file_bytes)
        results = []
        for i, img_bytes in enumerate(page_images):
            try:
                res = analyze_medical_image(img_bytes, model)
                res['page_number'] = i + 1
                results.append(res)
            except Exception as e:
                logger.error(f"Page {i+1} failed: {e}")
                results.append({'error': str(e), 'page_number': i+1})
        
        return _segregate_reports_by_type(results)
    else:
        logger.info("Processing single image...")
        res = analyze_medical_image(file_bytes, model)
        return [res]