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
Look closely at the top and bottom of the page for Patient Name and Report Date.

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
      "test_name": "EXACT test name as printed (e.g. 'HBsAg Screening' NOT 'Hemoglobin', 'HIV I & II' NOT 'HIV Test')",
      "value": "Primary result value - for qualitative tests (Non-Reactive/Reactive/Positive/Negative), use the TEXT result NOT the numeric ratio",
      "unit": "Unit of measurement if any, otherwise null",
      "reference_range": "Normal/reference range exactly as shown on the report, or null ONLY if truly not printed anywhere",
      "status": "MUST be one of: 'Normal', 'High', or 'Low' based on comparing the value to the reference_range. For qualitative tests, 'Non-Reactive' or 'Negative' = 'Normal', 'Reactive' or 'Positive' = 'High'"
    }
  ]
}

CRITICAL ANTI-HALLUCINATION RULES (STRICTLY ENFORCE):
1. TRANSCRIBE TEST NAMES EXACTLY: Copy the test name character-by-character from the report. DO NOT:
   - Autocomplete abbreviations (e.g., "HBsAg" must NOT become "Hemoglobin")
   - Replace names with synonyms (e.g., keep "HBsAg Screening" not "Hepatitis B Surface Antigen")
   - Guess or infer test names
   - CONFUSE "HBsAg" (Hepatitis B) with "Hb" (Hemoglobin). They are completely different tests.
   
2. IGNORE SECTION HEADERS: Section headers like "Thyroid Antibodies-TPO and ATG" or "HEMATOLOGY" are NOT test results. Only extract rows that have:
   - A specific test name in the left column
   - A corresponding result value in the result column
   - DO NOT extract headers, category labels, or page footers
   
3. QUALITATIVE TESTS (HIV/HCV/HBsAg/RPR/VDRL/Pregnancy): For these tests:
   - PRIMARY VALUE: Use the TEXT result (e.g., "Non-Reactive", "Reactive", "Positive", "Negative")
   - IGNORE numeric ratios like "S/CO: 0.2" - these are NOT the result
   - The text interpretation is the authoritative result
   
4. QUANTITATIVE TESTS (Hemoglobin/WBC/Glucose/etc.): 
   - Extract the NUMERIC value (e.g., "13.5", "5100")
   - Remove thousands separators (5,100 → 5100)
   - Include the unit (e.g., "g/dL", "cells/µL")
   
5. Return ONLY valid JSON - no explanations, no markdown, no code blocks.

6. Extract ALL visible test results on this page - do not stop early. Scan the entire image.

7. For reference_range, COPY the exact range from the report (including units and symbols).

8. STANDARDIZED TEST NAMES: Only standardize COMMON abbreviations when the full name is clear:
   - "Hb" → "Hemoglobin" (ONLY if it says "Hb" not "HBsAg")
   - "WBC" → "Total Leukocyte Count"
   - "RBC" → "Red Blood Cell Count"
   - "PLT" → "Platelet Count"
   - For specialized tests (HBsAg, HIV, HCV, RPR, VDRL), keep the EXACT name from the report

9. STATUS EXTRACTION: 
   - For QUANTITATIVE tests: Compare value to reference_range
     * If value < lower bound → "Low"
     * If value > upper bound → "High"
     * If value within range → "Normal"
     
10. MISSING INFO: If Patient Name or Date is not clearly labeled, look for text like "Name:", "Patient:", "Date:", "Reported:", "Collected:".
   - For QUALITATIVE tests:
     * "Non-Reactive", "Negative", "Normal" → "Normal"
     * "Reactive", "Positive", "Abnormal" → "High"
   - If the report explicitly marks it as abnormal/high/low, use that marking

10. Double-check your JSON is valid and matches the structure above.

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
    original_text = text  # Keep for debugging
    
    try:
        # 1. Remove Markdown Code Blocks (```json ... ```)
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)

        # 2. Isolate the JSON block
        start_index = text.find('{')
        # Use rfind to find the last '}', but if it's missing (truncation), use the end of string
        end_index = text.rfind('}')
        
        if start_index == -1:
            logger.error("No JSON start brace found in response")
            raise json.JSONDecodeError("No JSON found", text, 0)
            
        if end_index == -1:
            # Truncated response? Use end of string
            text = text[start_index:]
        else:
            text = text[start_index : end_index + 1]

        # 3. Remove Comments (// ... or # ...)
        text = re.sub(r'//.*', '', text) 
        text = re.sub(r'#.*', '', text)

        # 4. FIX TRAILING COMMAS (The most common error)
        # Replaces ", }" with "}" and ", ]" with "]"
        text = re.sub(r',\s*([\]}])', r'\1', text)

        # 5. Attempt to parse
        parsed = json.loads(text)
        
        # 6. Validate the structure
        if not isinstance(parsed, dict):
            raise ValueError("Response is not a JSON object")
            
        # Ensure tests is a list
        if 'tests' in parsed and not isinstance(parsed['tests'], list):
            parsed['tests'] = []
            
        return parsed
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing Failed at position {e.pos}")
        logger.error(f"Cleaned text:\n{text[:500]}")
        
        # Attempt to repair truncated JSON
        try:
            logger.info("Attempting to repair truncated JSON...")
            repaired_text = text.strip()
            
            # 1. Remove last comma if present
            if repaired_text.endswith(','):
                repaired_text = repaired_text[:-1]
                
            # 2. Close unclosed strings
            if repaired_text.count('"') % 2 != 0:
                repaired_text += '"'
                
            # 3. Balance brackets/braces
            # Simple heuristic: append missing closing brackets
            # Note: This assumes standard nesting order (tests -> test object)
            open_brackets = repaired_text.count('[')
            close_brackets = repaired_text.count(']')
            open_braces = repaired_text.count('{')
            close_braces = repaired_text.count('}')
            
            # Append needed closing characters
            # Usually we need to close objects first, then arrays, then main object
            # But since we don't track the stack, we'll try a common pattern
            
            # If we are inside a test object (more { than }), close it
            if open_braces > close_braces:
                repaired_text += '}' * (open_braces - close_braces)
                
            # If we are inside the tests array (more [ than ]), close it
            if open_brackets > close_brackets:
                repaired_text += ']' * (open_brackets - close_brackets)
                
            # If we still have unclosed main object (which we might have closed above if it was the only one)
            # Let's re-check
            final_open_braces = repaired_text.count('{')
            final_close_braces = repaired_text.count('}')
            if final_open_braces > final_close_braces:
                repaired_text += '}' * (final_open_braces - final_close_braces)

            parsed = json.loads(repaired_text)
            logger.info("Successfully repaired truncated JSON")
            
            if isinstance(parsed, dict):
                if 'tests' in parsed and not isinstance(parsed['tests'], list):
                    parsed['tests'] = []
                return parsed
                
        except Exception as repair_error:
            logger.warning(f"JSON repair failed: {repair_error}")

        # Return a structured error instead of crashing
        return {
            "report_type": "JSON Parse Error",
            "patient_name": None,
            "report_date": None,
            "error": f"JSON Parsing Failed: {str(e)}",
            "raw_snippet": text[:200],
            "tests": []
        }
    except Exception as e:
        logger.error(f"Unexpected error during JSON extraction: {str(e)}")
        return {
            "report_type": "Extraction Error",
            "patient_name": None,
            "report_date": None,
            "error": str(e),
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
    Uses strict temperature settings to reduce hallucination.
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
            messages=[{
                'role': 'user', 
                'content': VISION_PROMPT, 
                'images': [base64_image]
            }],
            options={
                'temperature': 0.0,  # Zero temperature for maximum determinism and accuracy
                'num_ctx': 8192,      # CRITICAL: Increase context window (default is 2048, which is too small for images)
                'num_predict': 4096,  # Max tokens to generate
                'top_p': 0.9,  # Nucleus sampling for consistency
                'repeat_penalty': 1.1  # Prevent repetitive hallucinations
            }
        )
        
        if not response or 'message' not in response:
            raise ValueError("Invalid response from Ollama")
        
        response_text = response['message']['content']
        logger.debug(f"Raw vision response (first 300 chars): {response_text[:300]}")
        
        extracted = _extract_json_from_response(response_text)
        
        # Validation: warn if no tests found
        if not extracted.get('tests') or len(extracted.get('tests', [])) == 0:
            logger.warning("Vision model returned zero tests - possible empty page or parsing failure")
        
        return extracted
        
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
    Filters out empty or error pages.
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for page in page_results:
        # If the page failed, group it under "Error"
        if 'error' in page:
            grouped[f"error_{page.get('page_number')}"].append(page)
        # Skip pages with no tests (empty or non-medical pages)
        elif not page.get('tests') or len(page.get('tests', [])) == 0:
            logger.warning(f"Page {page.get('page_number', '?')} has no tests, skipping")
            continue
        else:
            # Handle cases where report_type might be messy
            rtype = page.get('report_type', 'Unknown')
            if not isinstance(rtype, str): 
                rtype = 'Unknown'
            # Normalize report type to avoid fragmentation
            rtype = rtype.strip().lower()
            grouped[rtype].append(page)
    
    merged_reports = []
    for rtype, pages in grouped.items():
        if rtype.startswith('error_'):
            merged_reports.extend(pages)
            continue
            
        merged = {
            'report_type': rtype.title() if rtype != 'unknown' else 'Medical Report',
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
    ENSURES ALL PAGES ARE PROCESSED - errors on individual pages won't stop processing.
    """
    if not file_bytes:
        raise ValueError("Empty file")

    is_pdf = _is_pdf(file_bytes)
    
    if is_pdf:
        logger.info("Processing PDF...")
        page_images = _convert_pdf_to_images(file_bytes)
        total_pages = len(page_images)
        logger.info(f"PDF converted to {total_pages} pages")
        
        results = []
        failed_pages = []
        
        for i, img_bytes in enumerate(page_images):
            page_num = i + 1
            try:
                logger.info(f"Processing page {page_num}/{total_pages}...")
                res = analyze_medical_image(img_bytes, model)
                res['page_number'] = page_num
                
                # Validate that the page has tests
                if res.get('tests') and len(res.get('tests', [])) > 0:
                    logger.info(f"✓ Page {page_num}: Found {len(res.get('tests', []))} tests")
                    results.append(res)
                else:
                    logger.warning(f"⚠ Page {page_num}: No tests found (might be a cover page or blank)")
                    # Still append it but mark it
                    res['warning'] = 'No tests found on this page'
                    results.append(res)
                    
            except Exception as e:
                # Log the error but DON'T stop processing other pages
                logger.error(f"❌ Page {page_num} failed: {e}")
                failed_pages.append(page_num)
                results.append({
                    'error': str(e), 
                    'page_number': page_num,
                    'tests': []
                })
        
        # Log final summary
        successful_pages = total_pages - len(failed_pages)
        logger.info(f"\n{'='*60}")
        logger.info(f"PDF Processing Complete:")
        logger.info(f"  Total Pages: {total_pages}")
        logger.info(f"  Successful: {successful_pages}")
        logger.info(f"  Failed: {len(failed_pages)}")
        if failed_pages:
            logger.warning(f"  Failed page numbers: {failed_pages}")
        logger.info(f"{'='*60}\n")
        
        # Return all results (including errors) - segregation will filter them
        return _segregate_reports_by_type(results)
    else:
        logger.info("Processing single image...")
        res = analyze_medical_image(file_bytes, model)
        res['page_number'] = 1
        return [res]