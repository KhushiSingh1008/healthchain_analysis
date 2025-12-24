"""
Vision-based LLM service for analyzing medical reports using Llama 3.2 Vision.
Supports multi-page PDFs, automatic report type segregation, and ROBUST JSON cleaning.
"""
import base64
import io
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

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

VISION_PROMPT = """You are a medical data assistant analyzing medical laboratory reports.

Carefully examine this image and extract ALL test results into a structured JSON format.

Your ENTIRE reply MUST be a SINGLE JSON object. Do NOT include:
- Headings
- Bullet points
- Explanations
- Markdown formatting
- Any text before or after the JSON

Your response MUST:
- Start with '{'
- End with '}'
- Be directly parseable as JSON.

Required JSON structure:
{
  "report_type": "Type of report if visible (e.g. blood_test, urine_analysis, xray), otherwise null",
  "patient_name": "Patient's name if visible, otherwise null",
  "report_date": "Report date in YYYY-MM-DD format if visible, otherwise null",
  "tests": [
    {
      "test_name": "Standardized formal medical test name (e.g. 'Hemoglobin' not 'Hb', 'Total Leukocyte Count' not 'WBC')",
      "value": "Test result value (no thousands separators, e.g. 5100 not 5,100)",
      "unit": "Unit of measurement",
      "reference_range": "Normal/reference range exactly as shown on the report, or null ONLY if truly not printed anywhere",
      "status": "MUST be one of: 'Normal', 'High', or 'Low' based on comparing the value to the reference_range shown on the report. If the report explicitly marks it as abnormal/high/low, use that. Otherwise, compare value to reference_range and set accordingly."
    }
  ]
}

CRITICAL INSTRUCTIONS (DO NOT IGNORE):
1. Return ONLY valid JSON - no explanations, no markdown, no code blocks.
2. Do NOT output section titles like '**Report Details**' or numbered/bulleted lists.
3. Extract ALL tests visible in the image.
4. If a field is not visible, use null.
5. Preserve exact values and units as shown (except remove thousands separators in numbers).
6. For tables, extract each row as a separate test.
7. Double-check that your response is valid JSON and matches the structure above.
8. For reference_range, always COPY the range from the report if present (including units and symbols).
9. STANDARDIZED TEST NAMES: Use formal medical terminology. Map abbreviations to full names:
   - "Hb" or "HGB" → "Hemoglobin"
   - "WBC" → "Total Leukocyte Count"
   - "RBC" → "Red Blood Cell Count"
   - "PLT" → "Platelet Count"
   - "HCT" → "Hematocrit"
   - "MCV" → "Mean Corpuscular Volume"
   - "MCH" → "Mean Cell Hemoglobin"
   - "MCHC" → "Mean Cell Hemoglobin Concentration"
   - Use full formal names whenever possible.
10. STATUS EXTRACTION: For EVERY test, you MUST set the "status" field to "Normal", "High", or "Low" by:
    - Comparing the test value to the reference_range shown on the report
    - If value is below the lower bound → "Low"
    - If value is above the upper bound → "High"
    - If value is within the range → "Normal"
    - If the report explicitly marks it as abnormal, use that marking
    - DO NOT leave status as null unless absolutely no reference_range exists

Now analyze the medical report image and return ONLY the JSON object, with no additional text."""

CLINICAL_RISK_SYSTEM_PROMPT = """You are a Clinical Diagnostic Expert. Analyze the following lab results.

Focus only on 'High' or 'Low' flagged values.

Explain the physiological significance of these abnormalities.

List 3-4 specific follow-up questions the patient should ask their doctor.

Use professional but empathetic language. Include a medical disclaimer."""


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


def _parse_float(value: Any) -> Optional[float]:
    """Best-effort conversion of a value (string/number) to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = value.replace(",", " ").strip()
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_reference_range(range_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse a reference range string into numeric (low, high) bounds where possible.
    Supports forms like:
      - '13.5 - 17.5'
      - '70–110 mg/dL'
      - '< 150'
      - '> 4.5'
    Returns (low, high) where either side can be None if not applicable.
    """
    if not range_str or not isinstance(range_str, str):
        return None, None

    text = range_str.replace(",", " ").replace("–", "-")

    # Case 1: interval "low - high"
    interval_match = re.search(r"(-?\d*\.?\d+)\s*-\s*(-?\d*\.?\d+)", text)
    if interval_match:
        try:
            low = float(interval_match.group(1))
            high = float(interval_match.group(2))
            return low, high
        except ValueError:
            return None, None

    # Case 2: "<= x" or "< x"
    upper_match = re.search(r"[<≤]\s*(-?\d*\.?\d+)", text)
    if upper_match:
        try:
            high = float(upper_match.group(1))
            return None, high
        except ValueError:
            return None, None

    # Case 3: ">= x" or "> x"
    lower_match = re.search(r"[>≥]\s*(-?\d*\.?\d+)", text)
    if lower_match:
        try:
            low = float(lower_match.group(1))
            return low, None
        except ValueError:
            return None, None

    return None, None


def flag_results(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically flag each test as 'Low', 'Normal', or 'High' based on reference_range.
    Also applies standardization (test names, dates) and computes risk scores.

    - Parses numeric value from test["value"]
    - Parses numeric bounds from test["reference_range"]
    - Sets/overwrites test["status"] with one of: 'Low', 'Normal', 'High'
      when both value and some bound(s) can be parsed.
    - Applies test name standardization
    - Computes risk_score for each test
    - Normalizes report_date to ISO format

    Returns the same report dict (modified in place for convenience).
    """
    # Import utils here to avoid circular imports
    from app.utils.medical_utils import (
        normalize_date,
        standardize_test_name,
        get_risk_score,
    )

    # Normalize report date
    if "report_date" in report:
        normalized_date = normalize_date(report.get("report_date"))
        if normalized_date:
            report["standardized_date"] = normalized_date
        else:
            report["standardized_date"] = report.get("report_date")

    tests = report.get("tests", [])
    if not isinstance(tests, list):
        return report

    risk_scores = []

    for test in tests:
        if not isinstance(test, dict):
            continue

        # Standardize test name
        original_name = test.get("test_name")
        if original_name:
            standardized_name = standardize_test_name(original_name)
            test["standardized_test_name"] = standardized_name
            # Also update the original field for backward compatibility
            test["test_name"] = standardized_name

        value_num = _parse_float(test.get("value"))
        ref_range = test.get("reference_range")
        if value_num is None or not ref_range:
            # Cannot compute deterministic flag, but still compute risk score
            status = test.get("status")
            risk_score = get_risk_score(status)
            test["risk_score"] = risk_score
            risk_scores.append(risk_score)
            continue

        low, high = _parse_reference_range(ref_range)
        status: Optional[str] = None

        if low is not None and high is not None:
            if value_num < low:
                status = "Low"
            elif value_num > high:
                status = "High"
            else:
                status = "Normal"
        elif low is not None:
            # Only lower bound known (e.g. '> 4.5')
            status = "Low" if value_num < low else "Normal"
        elif high is not None:
            # Only upper bound known (e.g. '< 150')
            status = "High" if value_num > high else "Normal"

        if status:
            test["status"] = status

        # Compute risk score
        risk_score = get_risk_score(status)
        test["risk_score"] = risk_score
        risk_scores.append(risk_score)

    # Compute average risk score for the report
    if risk_scores:
        report["risk_score_avg"] = sum(risk_scores) / len(risk_scores)
    else:
        report["risk_score_avg"] = 0.0

    return report


def run_clinical_risk_analysis(
    flagged_report: Dict[str, Any],
    model: str = "llama3.2",
) -> str:
    """
    Call a text-only Llama 3.2 model to perform clinical risk reasoning
    based on the deterministically flagged lab results.
    """
    if ollama is None:
        raise Exception("ollama package not installed. Run: pip install ollama")

    try:
        payload = json.dumps(flagged_report, ensure_ascii=False)
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": CLINICAL_RISK_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Here are the lab results in JSON format. "
                        "Focus your analysis only on tests with status 'High' or 'Low'.\n\n"
                        f"{payload}"
                    ),
                },
            ],
            options={"temperature": 0.2},
        )

        if not response or "message" not in response:
            raise ValueError("Invalid response from Ollama clinical model")

        return response["message"]["content"]
    except Exception as e:
        logger.error(f"Clinical risk analysis failed: {str(e)}")
        raise

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
            options={
                'temperature': 0.1,  # Slightly higher than 0 for deterministic but flexible JSON
                'num_predict': 2048  # Ensure JSON isn't cut off mid-response
            }
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