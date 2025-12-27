"""
FastAPI application for medical report analysis using Vision LLM.
Supports multi-page PDFs and automatic report type segregation.
"""
from typing import Any, List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your Vision + risk analysis services
from app.services.llm import (
    analyze_medical_document,
    flag_results,
    run_clinical_risk_analysis,
)

# Initialize FastAPI app
app = FastAPI(
    title="HealthChain Analysis - Medical Report Vision Analysis",
    description="Microservice for analyzing medical reports using Llama 3.2 Vision. Supports multi-page PDFs with automatic report type segregation.",
    version="3.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TestResult(BaseModel):
    test_name: str
    standardized_test_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = None
    risk_score: Optional[int] = None


class RiskExtractedData(BaseModel):
    report_type: Optional[str] = None
    patient_name: Optional[str] = None
    report_date: Optional[str] = None
    standardized_date: Optional[str] = None
    page_numbers: List[int] = []
    tests: List[TestResult]
    risk_score_avg: Optional[float] = None


class RiskAnalysisResponse(BaseModel):
    extracted_data: RiskExtractedData
    clinical_analysis: Optional[str] = None
    warning: Optional[str] = None


# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif"}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "HealthChain Analysis - Vision",
        "version": "3.0.0",
        "architecture": "Vision-First (Llama 3.2 Vision)",
        "features": [
            "Multi-page PDF support",
            "Automatic report type detection",
            "Report segregation by type",
            "Blood test, urine analysis, ECG, echo, and more"
        ],
        "status": "running",
        "endpoints": {
            "analyze": "/analyze (POST)",
            "health": "/health (GET)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "healthchain_analysis",
        "architecture": "vision-first"
    }


@app.post("/analyze")
async def analyze_medical_report(file: UploadFile = File(...)):
    """
    Analyze a medical report using Vision LLM.
    
    Supports:
    - Single images (PNG, JPG, JPEG, BMP, TIFF)
    - Multi-page PDFs
    - Automatic report type detection
    - Report segregation (blood, urine, echo, etc.)
    
    Returns:
    - For single-page documents: Single report object
    - For multi-page PDFs: Array of reports segregated by type
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    
    try:
        # Read file bytes
        print("\n" + "=" * 60)
        print("🔍 STARTING VISION ANALYSIS")
        print("=" * 60)
        print(f"File: {file.filename}")
        print(f"Type: {file_ext.upper()}")
        
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        print(f"Size: {len(file_bytes)} bytes")
        print("=" * 60 + "\n")
        
        # Analyze with vision model (handles both images and PDFs)
        print("🤖 ANALYZING WITH LLAMA 3.2 VISION MODEL...\n")
        
        results = analyze_medical_document(file_bytes)
        
        print("✅ VISION ANALYSIS COMPLETE!")
        print(f"   Reports found: {len(results)}")
        for i, report in enumerate(results, 1):
            report_type = report.get('report_type', 'unknown')
            test_count = len(report.get('tests', []))
            pages = report.get('page_numbers', [1])
            print(f"   Report {i}: {report_type} ({test_count} tests, pages: {pages})")
        print("=" * 60 + "\n")
        
        # Return result
        # If single report, return it directly for backward compatibility
        # If multiple reports, return array
        if len(results) == 1:
            return {
                "success": True,
                "filename": file.filename,
                "data": results[0]
            }
        else:
            return {
                "success": True,
                "filename": file.filename,
                "reports": results,
                "summary": {
                    "total_reports": len(results),
                    "report_types": [r.get("report_type") for r in results],
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


def _safe_float(value: Any) -> Optional[float]:
    """Best-effort helper to convert extracted values into floats for the response model."""
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return None
        cleaned = value.replace(",", " ").strip()
        import re as _re

        match = _re.search(r"[-+]?\d*\.?\d+", cleaned)
        if not match:
            return None
        return float(match.group(0))
    except Exception:
        return None


def _build_risk_extracted_data(report: dict) -> RiskExtractedData:
    """Normalize a raw report dict from the vision pipeline into the RiskExtractedData schema."""
    tests_raw = report.get("tests", []) or []
    tests: List[TestResult] = []

    for t in tests_raw:
        if not isinstance(t, dict):
            continue
        tests.append(
            TestResult(
                test_name=t.get("test_name") or "",
                standardized_test_name=t.get("standardized_test_name"),
                value=_safe_float(t.get("value")),
                unit=t.get("unit"),
                reference_range=t.get("reference_range"),
                status=t.get("status"),
                risk_score=t.get("risk_score"),
            )
        )

    return RiskExtractedData(
        report_type=report.get("report_type"),
        patient_name=report.get("patient_name"),
        report_date=report.get("report_date"),
        standardized_date=report.get("standardized_date"),
        page_numbers=report.get("page_numbers") or [],
        tests=tests,
        risk_score_avg=report.get("risk_score_avg"),
    )


@app.post("/analyze/risk", response_model=RiskAnalysisResponse)
async def analyze_clinical_risk(file: UploadFile = File(...)):
    """
    Single-report Clinical Risk Analysis.

    Pipeline:
    1) Vision extraction (existing v3.0 pipeline) to get structured tests
    2) Deterministic flagging of each test as Low / Normal / High
    3) Clinical reasoning via text-only Llama 3.2 model
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    try:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # STEP A: Vision extraction (re-use existing multi-page logic)
        reports = analyze_medical_document(file_bytes)
        if not reports:
            raise HTTPException(
                status_code=500,
                detail="Vision model returned no reports for this document",
            )

        # Filter out error pages
        valid_reports = [r for r in reports if 'error' not in r]
        if not valid_reports:
            raise HTTPException(
                status_code=500,
                detail="All pages failed to process. Please check the PDF quality.",
            )

        # For multipage PDFs: merge all tests from all valid reports into one
        if len(valid_reports) > 1:
            primary_report = {
                'report_type': valid_reports[0].get('report_type') or 'Multipage Report',
                'patient_name': next((r.get('patient_name') for r in valid_reports if r.get('patient_name')), None),
                'report_date': next((r.get('report_date') for r in valid_reports if r.get('report_date')), None),
                'tests': [],
                'page_numbers': []
            }
            
            # Merge all tests from all pages
            for report in valid_reports:
                primary_report['tests'].extend(report.get('tests', []))
                if 'page_numbers' in report:
                    primary_report['page_numbers'].extend(report['page_numbers'])
                elif 'page_number' in report:
                    primary_report['page_numbers'].append(report['page_number'])
        else:
            primary_report = valid_reports[0]

        # STEP B: Deterministic flagging
        flagged_report = flag_results(primary_report)

        # Build standardized extracted_data payload
        extracted_data = _build_risk_extracted_data(flagged_report)

        # STEP C: Clinical reasoning (best-effort; failure should not break extraction)
        clinical_text: Optional[str] = None
        warning: Optional[str] = None
        try:
            clinical_text = run_clinical_risk_analysis(
                {
                    "report_type": flagged_report.get("report_type"),
                    "patient_name": flagged_report.get("patient_name"),
                    "report_date": flagged_report.get("report_date"),
                    "tests": flagged_report.get("tests", []),
                }
            )
        except Exception as e:
            warning = (
                "Clinical reasoning step failed; returning extracted lab data only. "
                f"Details: {str(e)}"
            )

        return RiskAnalysisResponse(
            extracted_data=extracted_data,
            clinical_analysis=clinical_text,
            warning=warning,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True if you want auto-reload during development
        log_level="info"
    )