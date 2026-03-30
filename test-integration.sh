#!/bin/bash

# Frontend & Backend Integration Test Script
# This script validates the frontend-backend connection and data flow

set -e

echo "=========================================="
echo "Awana Points Logger - Integration Test"
echo "=========================================="
echo

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8000"
TEST_TOKEN="dev-token"

failed_tests=0
passed_tests=0

# Test function
run_test() {
  local test_name=$1
  local test_command=$2
  
  echo -n "Testing: $test_name... "
  
  if eval "$test_command" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((passed_tests++))
  else
    echo -e "${RED}✗ FAIL${NC}"
    ((failed_tests++))
  fi
}

echo "Backend Connectivity Tests"
echo "=========================="
echo

# Test 1: Backend Health
run_test "Backend Health Check" \
  "curl -s $API_URL/health | grep -q 'ok'"

# Test 2: API Documentation
run_test "API Documentation (Swagger UI)" \
  "curl -s -I $API_URL/docs | grep -q '200'"

# Test 3: OpenAPI Schema
run_test "OpenAPI Schema Available" \
  "curl -s $API_URL/openapi.json | grep -q 'paths'"

echo
echo "API Endpoint Tests"
echo "=================="
echo

# Test 4: Health Endpoint
run_test "GET /health" \
  "curl -s $API_URL/health | grep -q 'Awana Points Logger API'"

# Test 5: Classes Endpoint
run_test "GET /sheets/classes" \
  "curl -s $API_URL/sheets/classes | grep -q 'Boys'"

# Test 6: Points Sheet Endpoint (with token)
run_test "GET /sheets/PointsLogSheet (auth)" \
  "curl -s -H 'Authorization: Bearer $TEST_TOKEN' $API_URL/sheets/PointsLogSheet | grep -q 'data'"

# Test 7: Auth Endpoint (POST)
run_test "POST /auth/token (endpoint exists)" \
  "curl -s -I -X POST $API_URL/auth/token | grep -q '400\\|401\\|422'"

echo
echo "Integration Verification"
echo "========================"
echo

# Test 8: Environment Configuration
if [ -f "backend/.env" ]; then
  echo -e "${GREEN}✓${NC} Backend .env file exists"
  ((passed_tests++))
else
  echo -e "${RED}✗${NC} Backend .env file missing"
  ((failed_tests++))
fi

# Test 9: Frontend dependencies
if [ -f "package.json" ]; then
  echo -e "${GREEN}✓${NC} Frontend package.json exists"
  ((passed_tests++))
else
  echo -e "${RED}✗${NC} Frontend package.json missing"
  ((failed_tests++))
fi

# Test 10: Frontend App code
if grep -q "const API_BASE_URL" "App.js" 2>/dev/null; then
  echo -e "${GREEN}✓${NC} Frontend App.js configured"
  ((passed_tests++))
else
  echo -e "${RED}✗${NC} Frontend App.js not configured"
  ((failed_tests++))
fi

echo
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$passed_tests${NC}"
echo -e "Failed: ${RED}$failed_tests${NC}"
echo

if [ $failed_tests -eq 0 ]; then
  echo -e "${GREEN}✓ All tests passed!${NC}"
  echo
  echo "Next Steps:"
  echo "1. Install frontend dependencies: npm install"
  echo "2. Start backend: cd backend && source venv/bin/activate && python main.py"
  echo "3. Start frontend: npm start"
  echo "4. Open http://localhost:19006 in browser (for Expo Web)"
  exit 0
else
  echo -e "${RED}✗ Some tests failed${NC}"
  echo
  echo "Troubleshooting:"
  echo "- Ensure backend is running: python main.py"
  echo "- Check backend URL: http://localhost:8000"
  echo "- Verify .env file has correct credentials"
  exit 1
fi
