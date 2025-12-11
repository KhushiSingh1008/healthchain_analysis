"""
FastAPI application for medical report analysis using Vision LLM.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.services.llm import analyze_medical_image

# Initialize FastAPI app
app = FastAPI(
    title="HealthChain Analysis - Medical Report Vision Analysis",
    description="Microservice for analyzing medical reports using Llama 3.2 Vision",
    version="2.0.0"
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
        "version": "2.0.0",
        "architecture": "Vision-First (Llama 3.2 Vision)",
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
    
    This endpoint:
    1. Reads the uploaded file
    2. Sends it directly to Llama 3.2 Vision model
    3. Returns extracted structured medical data
    
    No separate OCR step - the vision model handles everything!
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
        
        # Analyze with vision model
        print("🤖 SENDING TO LLAMA 3.2 VISION MODEL...\n")
        
        result = analyze_medical_image(file_bytes)
        
        print("✅ VISION ANALYSIS COMPLETE!")
        print(f"   Patient: {result.get('patient_name', 'N/A')}")
        print(f"   Date: {result.get('report_date', 'N/A')}")
        print(f"   Tests Found: {len(result.get('tests', []))}")
        print("="*60 + "\n")
        
        # Return result
        return {
            "success": True,
            "filename": file.filename,
            "data": result
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
        reload=False,
        log_level="info"
    )
