"""
Vision-based LLM service for analyzing medical reports using Llama 3.2 Vision.
"""
import base64
import json
import logging
import re
from typing import Any, Dict

# Try importing ollama
try:
    import ollama
except ImportError:
    ollama = None

logger = logging.getLogger(__name__)

VISION_PROMPT = """You are a medical data assistant analyzing medical laboratory reports.

Carefully examine this image and extract ALL test results into a structured JSON format.

Required JSON structure:
{
  "patient_name": "Patient's name if visible, otherwise null",
  "report_date": "Report date in YYYY-MM-DD format if visible, otherwise null",
  "tests": [
    {
      "test_name": "Name of the medical test",
      "value": "Test result value",
      "unit": "Unit of measurement",
      "reference_range": "Normal/reference range if shown",
      "status": "normal/abnormal/critical if indicated"
    }
  ]
}

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON - no explanations, no markdown, no code blocks
2. Extract ALL tests visible in the image
3. If a field is not visible, use null
4. Preserve exact values and units as shown
5. For tables, extract each row as a separate test
6. Double-check that your response is valid JSON

Now analyze the medical report image and return the JSON:"""


def _extract_json_from_response(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from model response.
    Uses robust string slicing to find the first '{' and last '}'.
    """
    try:
        # 1. Find the first '{'
        start_index = text.find('{')
        # 2. Find the last '}'
        end_index = text.rfind('}')
        
        if start_index != -1 and end_index != -1:
            # Slice the string to get only the JSON part
            json_str = text[start_index : end_index + 1]
            return json.loads(json_str)
        else:
            # Fallback: Try parsing the whole text if no braces found (unlikely)
            return json.loads(text)
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON. Raw content snippet: {text[:200]}...")
        raise ValueError(f"AI returned invalid JSON: {str(e)}")


def analyze_medical_image(file_bytes: bytes, model: str = "llama3.2-vision") -> Dict[str, Any]:
    """
    Analyze a medical report image using Llama 3.2 Vision model.
    """
    if ollama is None:
        raise Exception("ollama package not installed. Run: pip install ollama")
    
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Empty file provided")
    
    try:
        # Convert file bytes to base64 (required by Ollama)
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        logger.info(f"Calling Ollama vision model: {model}")
        
        # Call Ollama vision model
        response = ollama.chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': VISION_PROMPT,
                    'images': [base64_image]
                }
            ],
            options={'temperature': 0} # Strict mode
        )
        
        # Extract response text
        if not response or 'message' not in response:
            raise ValueError("Invalid response from Ollama")
        
        response_text = response['message']['content']
        logger.info(f"Received response from vision model ({len(response_text)} characters)")
        
        # Parse JSON from response
        parsed_data = _extract_json_from_response(response_text)
        
        # Validate structure
        if not isinstance(parsed_data, dict):
            raise ValueError("Response is not a JSON object")
        
        if 'tests' not in parsed_data:
            logger.warning("Response missing 'tests' field, adding empty list")
            parsed_data['tests'] = []
        
        logger.info(f"Successfully extracted {len(parsed_data.get('tests', []))} test results")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error during vision analysis: {str(e)}")
        # Allow the actual error to bubble up so we see it in the API response
        raise Exception(f"Vision analysis failed: {str(e)}")

# Legacy function for backward compatibility
def analyze_medical_text(text: str) -> list:
    logger.warning("analyze_medical_text called but not implemented in vision-first architecture")
    return []