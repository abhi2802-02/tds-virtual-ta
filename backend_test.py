import json
import base64
import subprocess
import sys
from datetime import datetime

class TDSVirtualAssistantAPITester:
    def __init__(self, base_url="https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, validate_func=None):
        """Run a single API test using curl"""
        url = f"{self.api_url}/{endpoint}".rstrip('/')
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            # Build curl command
            if method == 'GET':
                cmd = ['curl', '-s', '-w', '%{http_code}', url]
            elif method == 'POST':
                cmd = ['curl', '-s', '-w', '%{http_code}', '-X', 'POST', 
                       '-H', 'Content-Type: application/json', 
                       '-d', json.dumps(data), 
                       url]
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Execute curl command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Extract status code from the last line
            output = result.stdout
            status_code = int(output[-3:])  # Last 3 characters should be status code
            response_body = output[:-3]  # Everything except the last 3 characters
            
            status_success = status_code == expected_status
            
            # Try to parse JSON response
            try:
                response_data = json.loads(response_body)
                json_success = True
            except json.JSONDecodeError:
                response_data = response_body
                json_success = False
            
            # Run custom validation if provided
            validation_success = True
            validation_message = ""
            if validate_func and json_success:
                validation_success, validation_message = validate_func(response_data)
            
            success = status_success and (validate_func is None or validation_success)
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {status_code}")
                if validation_message:
                    print(f"   {validation_message}")
            else:
                print(f"❌ Failed - Expected status {expected_status}, got {status_code}")
                if not validation_success:
                    print(f"   Validation failed: {validation_message}")
            
            # Store test result
            self.test_results.append({
                "name": name,
                "success": success,
                "status_code": status_code,
                "expected_status": expected_status,
                "response": response_data,
                "validation_message": validation_message if not validation_success else ""
            })
            
            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "success": False,
                "error": str(e)
            })
            return False, {"error": str(e)}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200,
            validate_func=lambda data: (
                "message" in data and "status" in data,
                f"Response contains expected fields: {data}"
            )
        )

    def test_status_endpoint(self):
        """Test the status endpoint"""
        return self.run_test(
            "Status Endpoint",
            "GET",
            "status",
            200,
            validate_func=lambda data: (
                all(key in data for key in ["status", "data_loaded", "total_documents", "openai_configured"]),
                f"Status response contains all required fields: {list(data.keys())}"
            )
        )

    def test_question_endpoint(self, question):
        """Test the question answering endpoint"""
        return self.run_test(
            f"Question Endpoint - '{question[:30]}...' if len(question) > 30 else question",
            "POST",
            "",
            200,
            data={"question": question},
            validate_func=lambda data: (
                "answer" in data and "links" in data and isinstance(data["links"], list),
                f"Response contains answer and links: answer length={len(data.get('answer', ''))}, links count={len(data.get('links', []))}"
            )
        )

    def test_question_with_image(self, question, image_path=None):
        """Test the question answering endpoint with an image"""
        # If no image path provided, we'll just send an empty base64 string
        image_base64 = ""
        if image_path:
            try:
                with open(image_path, "rb") as image_file:
                    image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            except Exception as e:
                print(f"Warning: Could not read image file: {e}")
        
        return self.run_test(
            f"Question with Image - '{question[:30]}...' if len(question) > 30 else question",
            "POST",
            "",
            200,
            data={"question": question, "image": image_base64},
            validate_func=lambda data: (
                "answer" in data and "links" in data,
                f"Response contains answer and links: answer length={len(data.get('answer', ''))}, links count={len(data.get('links', []))}"
            )
        )

    def test_invalid_request(self):
        """Test with invalid request data"""
        return self.run_test(
            "Invalid Request",
            "POST",
            "",
            422,  # FastAPI returns 422 for validation errors
            data={"invalid_field": "This should fail"}
        )

    def print_summary(self):
        """Print a summary of all test results"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        # Print failed tests
        if self.tests_passed < self.tests_run:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result.get("success", False):
                    print(f"- {result['name']}")
                    if "error" in result:
                        print(f"  Error: {result['error']}")
                    elif "validation_message" in result and result["validation_message"]:
                        print(f"  Reason: {result['validation_message']}")
                    else:
                        print(f"  Status: Got {result.get('status_code')}, expected {result.get('expected_status')}")
        
        return self.tests_passed == self.tests_run

def main():
    # Setup
    tester = TDSVirtualAssistantAPITester()
    
    # Run tests
    print("Starting TDS Virtual Teaching Assistant API Tests")
    print("="*50)
    
    # Test basic endpoints
    tester.test_root_endpoint()
    tester.test_status_endpoint()
    
    # Test with sample questions from the frontend
    sample_questions = [
        "Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?",
        "What Python libraries are covered in the TDS course?",
        "How do I handle machine learning models in assignments?",
        "What are the key topics in Tools in Data Science?"
    ]
    
    for question in sample_questions:
        tester.test_question_endpoint(question)
    
    # Test with an invalid request
    tester.test_invalid_request()
    
    # Test with a question containing special characters
    tester.test_question_endpoint("What's the difference between t-SNE and PCA? Can you explain in <10 lines?")
    
    # Print summary
    success = tester.print_summary()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())