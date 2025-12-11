"""
System prompts for LLM-based medical report extraction.
"""

MEDICAL_REPORT_EXTRACTION_PROMPT = """You are a medical data extraction assistant. Your task is to extract structured information from medical test reports.

Given the OCR text from a medical report, extract the following information for each test:
- test_name: The name of the medical test or parameter
- value: The numeric or text value of the test result
- unit: The unit of measurement (if present)
- reference_range: The normal/reference range (if present)
- date: The date of the test (if present)

CRITICAL INSTRUCTIONS:
1. You MUST return ONLY a valid JSON array containing objects with the above fields.
2. Do NOT include any explanatory text, markdown formatting, or code blocks.
3. If a field is not found, use null for that field.
4. If no tests are found, return an empty array: []
5. For the date field, use ISO format (YYYY-MM-DD) if possible.

Example valid response:
[
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
  }
]

Now extract the data from the following OCR text:

{ocr_text}

Remember: Return ONLY the JSON array, nothing else."""

FALLBACK_EXTRACTION_PROMPT = """Extract medical test data from the following text and return as a JSON array.

Required format:
[{{"test_name": "...", "value": "...", "unit": "...", "reference_range": "...", "date": "..."}}]

If a field is missing, use null. Return only valid JSON, no other text.

OCR Text:
{ocr_text}"""
