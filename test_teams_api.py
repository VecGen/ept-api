#!/usr/bin/env python3
"""
Test script for the new Teams API endpoints
Tests both authenticated and unauthenticated endpoints
"""

import requests
import json

# Configuration
API_BASE = "http://localhost:8080"  # Change to your API URL
# API_BASE = "https://mnwpivaen5.us-east-1.awsapprunner.com"

def test_cors_preflight(endpoint):
    """Test CORS preflight request"""
    print(f"\n🔧 Testing CORS preflight for {endpoint}")
    
    try:
        response = requests.options(
            f"{API_BASE}{endpoint}",
            headers={
                "Origin": "https://bynixti6xn.us-east-1.awsapprunner.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  CORS Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("  ✅ CORS preflight passed")
            return True
        else:
            print("  ❌ CORS preflight failed")
            return False
            
    except Exception as e:
        print(f"  ❌ CORS preflight error: {str(e)}")
        return False

def test_public_endpoint():
    """Test the public endpoint without authentication"""
    print(f"\n🧪 Testing public endpoint: /api/teams/test-public")
    
    try:
        response = requests.get(
            f"{API_BASE}/api/teams/test-public",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://bynixti6xn.us-east-1.awsapprunner.com"
            }
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Public endpoint SUCCESS")
            print(f"  Data: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"  ❌ Public endpoint FAILED")
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Public endpoint ERROR: {str(e)}")
        return False

def test_authenticated_endpoint():
    """Test the authenticated endpoint"""
    print(f"\n🔐 Testing authenticated endpoint: /api/teams/list")
    
    # You'll need to replace this with a valid token
    # Get this from your frontend or by calling the login endpoint
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX3R5cGUiOiJhZG1pbiIsInN1YiI6ImFkbWluIiwiZXhwIjoxNzUwNDMxNDI0fQ.c1fGmqjGdFDVb2AjmNqiyccIaPFkFPtFzzjkrhE3Ing"
    
    try:
        response = requests.get(
            f"{API_BASE}/api/teams/list",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {test_token}",
                "Origin": "https://bynixti6xn.us-east-1.awsapprunner.com"
            }
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Authenticated endpoint SUCCESS")
            print(f"  Data: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"  ❌ Authenticated endpoint FAILED")
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Authenticated endpoint ERROR: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing New Teams API Endpoints")
    print("=" * 50)
    
    # Test CORS preflight for different endpoints
    cors_results = []
    cors_results.append(test_cors_preflight("/api/teams/test-public"))
    cors_results.append(test_cors_preflight("/api/teams/list"))
    
    # Test actual endpoints
    public_result = test_public_endpoint()
    auth_result = test_authenticated_endpoint()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"  CORS Tests: {sum(cors_results)}/{len(cors_results)} passed")
    print(f"  Public Endpoint: {'✅ PASS' if public_result else '❌ FAIL'}")
    print(f"  Auth Endpoint: {'✅ PASS' if auth_result else '❌ FAIL'}")
    
    if all(cors_results) and public_result:
        print("\n🎉 New Teams API is working correctly!")
        print("🔧 CORS issues should be resolved.")
    else:
        print("\n⚠️  Some tests failed. Check the API configuration.")

if __name__ == "__main__":
    main() 