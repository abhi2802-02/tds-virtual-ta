#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define API URL
API_URL="https://0611d488-7360-4f0e-9013-4cdc03adf146.preview.emergentagent.com/api"

# Function to run a test
run_test() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"
    
    echo -e "\n${BLUE}🔍 Testing ${name}...${NC}"
    
    # Build and execute curl command
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${API_URL}/${endpoint}")
    elif [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "${API_URL}/${endpoint}")
    fi
    
    # Extract status code (last line) and response body
    status_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    # Check if status code matches expected
    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ Passed - Status: $status_code${NC}"
        # Print a preview of the response
        echo -e "   Response preview: ${response_body:0:100}..."
        return 0
    else
        echo -e "${RED}❌ Failed - Expected status $expected_status, got $status_code${NC}"
        echo -e "   Response: $response_body"
        return 1
    fi
}

# Initialize counters
tests_run=0
tests_passed=0

echo "Starting TDS Virtual Teaching Assistant API Tests"
echo "=================================================="

# Test 1: Root endpoint
((tests_run++))
if run_test "Root API Endpoint" "GET" "" "" 200; then
    ((tests_passed++))
fi

# Test 2: Status endpoint
((tests_run++))
if run_test "Status Endpoint" "GET" "status" "" 200; then
    ((tests_passed++))
fi

# Test 3: Question endpoint with sample question 1
((tests_run++))
if run_test "Question Endpoint - Sample 1" "POST" "" '{"question": "Should I use gpt-4o-mini which AI proxy supports, or gpt3.5 turbo?"}' 200; then
    ((tests_passed++))
fi

# Test 4: Question endpoint with sample question 2
((tests_run++))
if run_test "Question Endpoint - Sample 2" "POST" "" '{"question": "What Python libraries are covered in the TDS course?"}' 200; then
    ((tests_passed++))
fi

# Test 5: Invalid request
((tests_run++))
if run_test "Invalid Request" "POST" "" '{"invalid_field": "This should fail"}' 422; then
    ((tests_passed++))
fi

# Print summary
echo -e "\n=================================================="
echo -e "${BLUE}📊 TEST SUMMARY: $tests_passed/$tests_run tests passed${NC}"
echo "=================================================="

# Return success if all tests passed
if [ "$tests_passed" -eq "$tests_run" ]; then
    exit 0
else
    exit 1
fi