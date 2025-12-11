@echo off
echo ====================================
echo HealthChain Analysis Microservice
echo ====================================
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

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Check if Ollama is accessible
echo Checking Ollama connection...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Cannot connect to Ollama at http://localhost:11434
    echo Please ensure Ollama is running with: ollama serve
    echo.
)

REM Start the service
echo Starting HealthChain Analysis service...
echo Service will be available at http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
python -m app.main
