"""
Sample client script to test the healthchain_analysis API.
"""
import requests
import json
import sys
from pathlib import Path


def analyze_report(file_path: str, api_url: str = "http://localhost:8000"):
    """
    Send a medical report to the analysis API.
    
    Args:
        file_path: Path to the medical report file
        api_url: Base URL of the API
    """
    endpoint = f"{api_url}/analyze"
    
    # Check if file exists
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        return None
    
    print(f"Analyzing file: {file_path}")
    print(f"API endpoint: {endpoint}")
    print("-" * 60)
    
    try:
        # Open and send the file
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            
            print("Sending request...")
            response = requests.post(endpoint, files=files, timeout=120)
        
        # Check response status
        if response.status_code == 200:
            print("✓ Analysis completed successfully!\n")
            result = response.json()
            
            # Display results
            print("=" * 60)
            print("ANALYSIS RESULTS")
            print("=" * 60)
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            print()
            
            # Display metadata
            metadata = result.get('metadata', {})
            print("Metadata:")
            print(f"  File Name: {metadata.get('file_name')}")
            print(f"  File Type: {metadata.get('file_type')}")
            print(f"  File Size: {metadata.get('file_size')} bytes")
            print(f"  OCR Text Length: {metadata.get('ocr_text_length')} characters")
            print(f"  Tests Found: {metadata.get('test_count')}")
            print()
            
            # Display OCR text (truncated)
            ocr_text = result.get('ocr_text', '')
            if ocr_text:
                print("OCR Text (preview):")
                print("-" * 60)
                print(ocr_text[:500])
                if len(ocr_text) > 500:
                    print("...")
                print("-" * 60)
                print()
            
            # Display extracted data
            extracted_data = result.get('extracted_data', [])
            if extracted_data:
                print(f"Extracted Test Results ({len(extracted_data)}):")
                print("=" * 60)
                for idx, test in enumerate(extracted_data, 1):
                    print(f"\n{idx}. Test: {test.get('test_name') or 'N/A'}")
                    print(f"   Value: {test.get('value') or 'N/A'}")
                    print(f"   Unit: {test.get('unit') or 'N/A'}")
                    print(f"   Reference Range: {test.get('reference_range') or 'N/A'}")
                    print(f"   Date: {test.get('date') or 'N/A'}")
            else:
                print("No test results extracted.")
            
            print("=" * 60)
            print()
            
            # Save full response to JSON file
            output_file = Path(file_path).stem + "_analysis.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Full results saved to: {output_file}")
            
            return result
            
        else:
            print(f"✗ Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("✗ Error: Cannot connect to API")
        print(f"Make sure the service is running at {api_url}")
        print("Start it with: python -m app.main")
        return None
    
    except requests.exceptions.Timeout:
        print("✗ Error: Request timed out")
        print("The file may be too large or processing is taking too long")
        return None
    
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return None


def test_health_endpoint(api_url: str = "http://localhost:8000"):
    """Test the health check endpoint."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Service is healthy")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot reach service: {str(e)}")
        return False


def main():
    """Main function for the test client."""
    print("=" * 60)
    print("HealthChain Analysis - Test Client")
    print("=" * 60)
    print()
    
    # Check if file path is provided
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <path_to_medical_report>")
        print()
        print("Example:")
        print("  python test_client.py sample_report.pdf")
        print("  python test_client.py blood_test.jpg")
        print()
        
        # Test health endpoint
        print("Testing health endpoint...")
        test_health_endpoint()
        return
    
    file_path = sys.argv[1]
    
    # Optional: custom API URL
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    # First, test health endpoint
    print("Testing service health...")
    if not test_health_endpoint(api_url):
        print("\nService is not available. Please start it first.")
        return
    
    print()
    
    # Analyze the report
    analyze_report(file_path, api_url)


if __name__ == "__main__":
    main()
