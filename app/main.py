"""
FastAPI application for medical report analysis using Vision LLM.
Supports multi-page PDFs and automatic report type segregation.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import your Vision service
from app.services.llm import analyze_medical_document

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

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}


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
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # Read file bytes
        print("\n" + "="*60)
        print("🔍 STARTING VISION ANALYSIS")
        print("="*60)
        print(f"File: {file.filename}")
        print(f"Type: {file_ext.upper()}")
        
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        print(f"Size: {len(file_bytes)} bytes")
        print("="*60 + "\n")
        
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
        print("="*60 + "\n")
        
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
                    "report_types": [r.get('report_type') for r in results]
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True if you want auto-reload during development
        log_level="info"
    )