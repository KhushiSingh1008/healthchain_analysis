"""
FastAPI application for medical report analysis using Vision LLM.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import io
import fitz  # PyMuPDF (Required for PDF handling)

# Import your Vision service
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
    Handles Images natively and converts PDFs to Images automatically.
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
        
        # --- 📄 PDF CONVERSION LOGIC (Added) ---
        if file_ext == 'pdf':
            print("📄 PDF detected. Converting first page to Image...")
            try:
                # Open PDF from bytes
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                # Load first page
                page = doc.load_page(0)
                # Render to image (High DPI for better quality)
                pix = page.get_pixmap(dpi=300)
                # Convert back to bytes (PNG format)
                file_bytes = pix.tobytes("png")
                print("✅ PDF converted to PNG image successfully.")
            except Exception as e:
                print(f"❌ PDF Conversion Failed: {str(e)}")
                raise HTTPException(status_code=400, detail="Failed to read PDF file. Please upload a valid Image.")
        # ---------------------------------------

        print("="*60 + "\n")
        
        # Analyze with vision model
        print("🤖 SENDING TO LLAMA 3.2 VISION MODEL...\n")
        
        # Now file_bytes is guaranteed to be an image (even if it started as PDF)
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
        reload=False,  # Set to True if you want auto-reload during development
        log_level="info"
    )