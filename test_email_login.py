#!/usr/bin/env python3
"""Test email login functionality"""

import requests
import json

def test_email_login():
    """Test the new email login endpoint"""
    
    print("🔑 Testing Email Login Endpoint")
    print("=" * 50)
    
    # Backend URL
    base_url = "https://mnwpivaen5.us-east-1.awsapprunner.com"
    
    # Test with a known email from teams config
    test_cases = [
        {
            "email": "alice@company.com",
            "password": "testpass123",
            "expected": "should fail - no password set"
        },
        {
            "email": "bob@company.com", 
            "password": "testpass123",
            "expected": "should fail - no password set"
        },
        {
            "email": "nonexistent@test.com",
            "password": "testpass123", 
            "expected": "should fail - user not found"
        }
    ]
    
    # Correct endpoint path - note it's NOT under /api/auth/
    endpoint = f"{base_url}/api/engineer/login-email"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📧 Test {i}: {test_case['email']}")
        print(f"Expected: {test_case['expected']}")
        print(f"Endpoint: {endpoint}")
        
        try:
            response = requests.post(
                endpoint,
                json={
                    "email": test_case["email"],
                    "password": test_case["password"]
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Login successful (unexpected)")
            elif response.status_code == 401:
                print("✅ Login failed as expected")
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - backend may be down")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test endpoint existence
    print(f"\n🔍 Testing endpoint existence...")
    try:
        response = requests.options(endpoint, timeout=5)
        print(f"OPTIONS request status: {response.status_code}")
        if response.status_code in [200, 405]:
            print("✅ Endpoint exists")
        else:
            print("❌ Endpoint may not exist")
    except Exception as e:
        print(f"❌ Error checking endpoint: {e}")

if __name__ == "__main__":
    test_email_login() 