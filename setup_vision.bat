@echo off
echo ============================================================
echo HealthChain Analysis - Vision Architecture Setup
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install minimal dependencies
echo Installing dependencies (much lighter than before!)...
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 python-multipart==0.0.6 ollama==0.4.4 pydantic==2.5.0 python-dotenv==1.0.0
echo.

REM Check if Ollama is accessible
echo Checking Ollama connection...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo WARNING: Cannot connect to Ollama
    echo ============================================================
    echo Please make sure:
    echo 1. Ollama is installed from https://ollama.ai/download
    echo 2. Run: ollama serve
    echo 3. Run: ollama pull llama3.2-vision
    echo ============================================================
    echo.
) else (
    echo ✓ Ollama is running!
    echo.
    echo Checking for llama3.2-vision model...
    curl -s http://localhost:11434/api/tags | findstr "llama3.2-vision" >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo Model not found. Pulling llama3.2-vision...
        echo This may take a few minutes on first run...
        ollama pull llama3.2-vision
    ) else (
        echo ✓ llama3.2-vision model found!
    )
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Start the service with:
echo   python -m app.main
echo.
echo Service will be available at: http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo ============================================================
pause
