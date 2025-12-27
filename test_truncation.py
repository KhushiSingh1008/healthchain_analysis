"""
Test script to verify truncation handling and JSON recovery.
"""
import json
import re
from typing import Dict, Any

def test_recovery(text: str, test_name: str):
    """Test the recovery logic on truncated JSON."""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Input length: {len(text)} chars")
    print(f"Input preview: {text[:100]}...")
    
    original_text = text
    
    # Extract JSON object
    start = text.find('{')
    end = text.rfind('}')
    
    print(f"\nStart brace at: {start}")
    print(f"End brace at: {end}")
    
    if end == -1 or end < start:
        print("⚠️  TRUNCATED - attempting recovery...")
        text = text[start:]
        
        # Find last complete test entry
        last_complete_test = text.rfind('},')
        print(f"Last complete test at: {last_complete_test}")
        
        if last_complete_test != -1:
            text = text[:last_complete_test + 1]
            text += '\n  ]\n}'
            print("✅ Recovered by closing at last complete test")
        else:
            print("❌ No complete tests found")
            return None
    else:
        text = text[start:end + 1]
        print("✅ Complete JSON found")
    
    # Clean up
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    # Try to parse
    try:
        parsed = json.loads(text)
        print(f"\n✅ SUCCESSFULLY PARSED")
        print(f"   Report: {parsed.get('report_type')}")
        print(f"   Patient: {parsed.get('patient_name')}")
        print(f"   Tests: {len(parsed.get('tests', []))}")
        for i, test in enumerate(parsed.get('tests', [])[:3], 1):
            print(f"   {i}. {test.get('test_name')}: {test.get('value')} {test.get('unit', '')}")
        if len(parsed.get('tests', [])) > 3:
            print(f"   ... and {len(parsed.get('tests', [])) - 3} more")
        return parsed
    except json.JSONDecodeError as e:
        print(f"\n❌ PARSING FAILED: {str(e)}")
        print(f"Cleaned text preview:\n{text[:200]}")
        return None


# Test Case 1: Truncated mid-test (your actual error)
truncated_response = """{
  "report_type": "Complete Blood Count",
  "patient_name": "Mr. Saubhik Bhaumik",
  "report_date": "17/10/2024 04:55 PM",
  "tests": [
    {
      "test_name": "Hemoglobin",
      "value": 15,
      "unit": "g/dl",
      "reference_range": "13-17",
      "status": "Normal"
    },
    {
      "test_name": "WBC Count",
      "value": 5100,
      "unit": "cells/cumm",
      "reference_range": "4000-11000",
      "status": "Normal"
    },
    {
      "test"""

# Test Case 2: Truncated after complete test
truncated_after_complete = """{
  "report_type": "Lipid Profile",
  "patient_name": "Jane Doe",
  "report_date": "2024-01-15",
  "tests": [
    {
      "test_name": "Total Cholesterol",
      "value": 180,
      "unit": "mg/dl",
      "reference_range": "< 200",
      "status": "Normal"
    },
    {
      "test_name": "HDL",
      "value": 55,
      "unit": "mg/dl",
      "reference_range": "> 40",
      "status": "Normal"
    },"""

# Test Case 3: Complete JSON (should work normally)
complete_json = """{
  "report_type": "Urine Analysis",
  "patient_name": "John Smith",
  "report_date": "2024-02-20",
  "tests": [
    {
      "test_name": "pH",
      "value": 6.5,
      "unit": "",
      "reference_range": "5.0-7.0",
      "status": "Normal"
    },
    {
      "test_name": "Specific Gravity",
      "value": 1.015,
      "unit": "",
      "reference_range": "1.005-1.030",
      "status": "Normal"
    }
  ]
}"""

# Run tests
print("\n" + "="*70)
print("TRUNCATION RECOVERY TEST SUITE")
print("="*70)

test_recovery(truncated_response, "Truncated mid-test (your error)")
test_recovery(truncated_after_complete, "Truncated after complete test")
test_recovery(complete_json, "Complete JSON (baseline)")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("""
The improved logic:
1. Detects truncation (missing closing brace)
2. Finds the last complete test object (ending with },)
3. Truncates to that point and properly closes the JSON
4. This preserves all complete tests instead of failing entirely

With num_predict increased to 4096, truncation should be much less common.
""")
