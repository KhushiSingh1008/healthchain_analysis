"""
Test script to verify the healthchain_analysis service setup.
"""
import sys
import importlib.util


def check_module(module_name: str) -> bool:
    """Check if a Python module is installed."""
    spec = importlib.util.find_spec(module_name)
    return spec is not None


def main():
    """Run setup verification tests."""
    print("=" * 60)
    print("HealthChain Analysis - Setup Verification")
    print("=" * 60)
    print()
    
    # Check Python version
    print("1. Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro} (OK)")
    else:
        print(f"   ✗ Python {version.major}.{version.minor}.{version.micro} (Need 3.9+)")
        return False
    print()
    
    # Check required modules
    print("2. Checking required Python packages...")
    required_modules = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'paddleocr': 'PaddleOCR',
        'paddle': 'PaddlePaddle',
        'pdf2image': 'pdf2image',
        'PIL': 'Pillow',
        'cv2': 'OpenCV',
        'requests': 'requests',
        'pydantic': 'Pydantic'
    }
    
    all_installed = True
    for module, name in required_modules.items():
        if check_module(module):
            print(f"   ✓ {name}")
        else:
            print(f"   ✗ {name} (Not installed)")
            all_installed = False
    print()
    
    if not all_installed:
        print("Some packages are missing. Install them with:")
        print("   pip install -r requirements.txt")
        print()
        return False
    
    # Check Ollama connection
    print("3. Checking Ollama connection...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✓ Ollama is running and accessible")
            
            # Check for llama3.2 model
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            if any('llama3.2' in model for model in models):
                print("   ✓ Llama 3.2 model is available")
            else:
                print("   ⚠ Llama 3.2 model not found. Install with:")
                print("     ollama pull llama3.2")
        else:
            print("   ✗ Ollama responded with error")
            all_installed = False
    except Exception as e:
        print(f"   ✗ Cannot connect to Ollama: {str(e)}")
        print("     Make sure Ollama is running with: ollama serve")
        all_installed = False
    print()
    
    # Check project structure
    print("4. Checking project structure...")
    import os
    required_files = [
        'app/__init__.py',
        'app/main.py',
        'app/services/__init__.py',
        'app/services/ocr.py',
        'app/services/llm.py',
        'app/utils/__init__.py',
        'app/utils/prompts.py',
        'requirements.txt'
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✓ {file_path}")
        else:
            print(f"   ✗ {file_path} (Missing)")
            all_files_exist = False
    print()
    
    # Summary
    print("=" * 60)
    if all_installed and all_files_exist:
        print("✓ Setup verification completed successfully!")
        print()
        print("You can now start the service with:")
        print("   python -m app.main")
        print()
        print("Or use the start script:")
        print("   start.bat (Windows)")
        print()
        print("Service will be available at: http://localhost:8000")
        print("API docs: http://localhost:8000/docs")
    else:
        print("✗ Setup verification failed. Please fix the issues above.")
    print("=" * 60)
    print()
    
    return all_installed and all_files_exist


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
