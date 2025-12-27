"""
Medical data normalization and standardization utilities.
Includes date normalization, test name mapping, and risk scoring.
"""
import logging
from typing import Dict, Optional

try:
    import dateparser
    DATE_PARSER_AVAILABLE = True
except ImportError:
    DATE_PARSER_AVAILABLE = False
    logging.warning("dateparser not installed. Date normalization will be limited.")

logger = logging.getLogger(__name__)

# Test name synonyms mapping (common abbreviations to standardized names)
TEST_SYNONYMS: Dict[str, str] = {
    # Hemoglobin variations
    "hgb": "Hemoglobin",
    "hb": "Hemoglobin",
    "hemoglobin": "Hemoglobin",
    "hgb (hemoglobin)": "Hemoglobin",
    
    # White Blood Cell variations
    "wbc": "Total Leukocyte Count",
    "white blood cell count": "Total Leukocyte Count",
    "total leukocyte count": "Total Leukocyte Count",
    "leukocyte count": "Total Leukocyte Count",
    
    # Red Blood Cell variations
    "rbc": "Red Blood Cell Count",
    "red blood cell count": "Red Blood Cell Count",
    "erythrocyte count": "Red Blood Cell Count",
    
    # Platelet variations
    "plt": "Platelet Count",
    "platelet count": "Platelet Count",
    "platelets": "Platelet Count",
    
    # Hematocrit variations
    "hct": "Hematocrit",
    "hematocrit": "Hematocrit",
    "hematocrit value": "Hematocrit",
    "hct (hematocrit)": "Hematocrit",
    
    # MCV variations
    "mcv": "Mean Corpuscular Volume",
    "mean corpuscular volume": "Mean Corpuscular Volume",
    "mean cell volume": "Mean Corpuscular Volume",
    
    # MCH variations
    "mch": "Mean Cell Hemoglobin",
    "mean cell hemoglobin": "Mean Cell Hemoglobin",
    "mean corpuscular hemoglobin": "Mean Cell Hemoglobin",
    
    # MCHC variations
    "mchc": "Mean Cell Hemoglobin Concentration",
    "mean cell hemoglobin concentration": "Mean Cell Hemoglobin Concentration",
    "mean corpuscular hemoglobin concentration": "Mean Cell Hemoglobin Concentration",
    
    # Glucose variations
    "glucose": "Glucose",
    "glucose fast": "Fasting Glucose",
    "fasting glucose": "Fasting Glucose",
    "blood glucose": "Glucose",
    "fbs": "Fasting Glucose",
    "fasting blood sugar": "Fasting Glucose",
    
    # Creatinine variations
    "creatinine": "Creatinine",
    "serum creatinine": "Creatinine",
    "creat": "Creatinine",
    
    # Urea/BUN variations
    "urea": "Urea",
    "bun": "Blood Urea Nitrogen",
    "blood urea nitrogen": "Blood Urea Nitrogen",
    
    # Differential counts
    "neutrophils": "Neutrophils",
    "lymphocytes": "Lymphocytes",
    "eosinophils": "Eosinophils",
    "monocytes": "Monocytes",
    "basophils": "Basophils",
    
    # Liver function tests
    "alt": "Alanine Aminotransferase",
    "sgot": "Alanine Aminotransferase",
    "ast": "Aspartate Aminotransferase",
    "sgpt": "Aspartate Aminotransferase",
    "bilirubin": "Total Bilirubin",
    "total bilirubin": "Total Bilirubin",
}


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize various date formats to ISO string (YYYY-MM-DD).
    
    Supports formats like:
    - "17/10/2024" -> "2024-10-17"
    - "Oct 12th 2024" -> "2024-10-12"
    - "2024-10-17" -> "2024-10-17" (already ISO)
    - "10/17/2024" -> "2024-10-17" (US format)
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO format date string (YYYY-MM-DD) or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str:
        return None
    
    # Try dateparser first (most flexible)
    if DATE_PARSER_AVAILABLE:
        try:
            parsed = dateparser.parse(date_str)
            if parsed:
                return parsed.strftime("%Y-%m-%d")
        except Exception as e:
            logger.debug(f"dateparser failed for '{date_str}': {e}")
    
    # Fallback: Try common patterns manually
    import re
    
    # Pattern 1: DD/MM/YYYY or MM/DD/YYYY
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
    if match:
        d, m, y = match.groups()
        # Heuristic: if first part > 12, assume DD/MM/YYYY, else MM/DD/YYYY
        if int(d) > 12:
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        else:
            return f"{y}-{d.zfill(2)}-{m.zfill(2)}"
    
    # Pattern 2: YYYY-MM-DD (already ISO)
    match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if match:
        y, m, d = match.groups()
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    
    # Pattern 3: DD-MM-YYYY
    match = re.match(r"(\d{1,2})-(\d{1,2})-(\d{4})", date_str)
    if match:
        d, m, y = match.groups()
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    
    logger.warning(f"Could not normalize date: '{date_str}'")
    return None


def standardize_test_name(test_name: Optional[str]) -> str:
    """
    Standardize test name using synonym mapping.
    
    First checks the TEST_SYNONYMS dictionary (case-insensitive),
    then returns the original name if no match is found.
    
    Args:
        test_name: Raw test name from the report
        
    Returns:
        Standardized test name
    """
    if not test_name or not isinstance(test_name, str):
        return test_name or ""
    
    test_name_lower = test_name.strip().lower()
    
    # Direct lookup
    if test_name_lower in TEST_SYNONYMS:
        return TEST_SYNONYMS[test_name_lower]
    
    # Check for partial matches (e.g., "Hb" in "Hb (Hemoglobin)")
    # Use word boundaries to avoid false positives (e.g. "Hb" matching "HBsAg")
    import re
    for key, standardized in TEST_SYNONYMS.items():
        # Escape key for regex
        key_esc = re.escape(key)
        # Check if key appears as a whole word in test_name_lower
        if re.search(r'\b' + key_esc + r'\b', test_name_lower):
            return standardized
        # Also check if test_name_lower appears in key (reverse match)
        # e.g. "leukocyte count" input matching "total leukocyte count" key
        # But ensure input is not too short to avoid false positives
        if len(test_name_lower) > 3 and test_name_lower in key:
            return standardized
    
    # No match found, return original (capitalized)
    return test_name.strip()


def get_risk_score(status: Optional[str]) -> int:
    """
    Map test status to risk score.
    
    Mapping:
    - "Normal" -> 0
    - "High" or "Low" -> 1
    - Missing/null -> 0 (with warning logged)
    
    Args:
        status: Test status string ("Normal", "High", "Low", or None)
        
    Returns:
        Risk score (0 or 1)
    """
    if not status:
        logger.warning(f"Missing status for test, defaulting risk_score to 0")
        return 0
    
    status_lower = status.lower().strip()
    
    if status_lower == "normal":
        return 0
    elif status_lower in {"high", "low"}:
        return 1
    else:
        # Unknown status, default to 0 but log warning
        logger.warning(f"Unknown status '{status}', defaulting risk_score to 0")
        return 0

