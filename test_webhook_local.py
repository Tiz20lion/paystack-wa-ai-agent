#!/usr/bin/env python3
"""
Local test script for WhatsApp webhook endpoint.
Tests the webhook without needing actual Twilio requests.
"""

import requests
import json
from urllib.parse import urlencode

# Configuration
BASE_URL = "http://localhost:8000"
WEBHOOK_URL = f"{BASE_URL}/whatsapp/webhook"

def test_health():
    """Test health endpoint."""
    print("=" * 60)
    print("1. Testing Health Endpoint")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("✅ Health check passed\n")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running?")
        print("   Start server with: python start.py --mode api")
        return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def test_webhook_without_signature():
    """Test webhook without Twilio signature (development mode)."""
    print("=" * 60)
    print("2. Testing Webhook Endpoint (Without Signature)")
    print("=" * 60)
    
    # Simulate WhatsApp message data
    test_data = {
        "From": "whatsapp:+1234567890",
        "Body": "hello",
        "MessageSid": "SM1234567890abcdef",
        "AccountSid": "AC1234567890abcdef",
        "To": "whatsapp:+14155238886"
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=test_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ Webhook test passed\n")
            return True
        else:
            print(f"⚠️  Webhook returned status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def test_webhook_with_balance():
    """Test webhook with balance request."""
    print("=" * 60)
    print("3. Testing Webhook with Balance Request")
    print("=" * 60)
    
    test_data = {
        "From": "whatsapp:+1234567890",
        "Body": "what's my balance",
        "MessageSid": "SM1234567890abcdef",
        "AccountSid": "AC1234567890abcdef",
        "To": "whatsapp:+14155238886"
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            data=test_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
        
        if response.status_code == 200:
            print("✅ Balance request test passed\n")
            return True
        else:
            print(f"⚠️  Request returned status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def test_api_endpoints():
    """Test API endpoints."""
    print("=" * 60)
    print("4. Testing API Endpoints")
    print("=" * 60)
    
    # Test info endpoint (requires API key)
    try:
        # This will fail without API key, but we can check the error
        response = requests.get(f"{BASE_URL}/api/info", timeout=5)
        print(f"Info endpoint status: {response.status_code}")
        if response.status_code == 401:
            print("✅ API key protection is working\n")
        else:
            print(f"Response: {response.json()}\n")
    except Exception as e:
        print(f"⚠️  Info endpoint test: {e}\n")
    
    # Test docs endpoint
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API docs accessible\n")
        else:
            print(f"⚠️  Docs endpoint status: {response.status_code}\n")
    except Exception as e:
        print(f"⚠️  Docs endpoint test: {e}\n")

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🧪 Local Webhook Testing Suite")
    print("=" * 60)
    print("\nMake sure your server is running:")
    print("  python start.py --mode api")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    
    if results[0][1]:  # Only continue if health check passed
        results.append(("Webhook (Hello)", test_webhook_without_signature()))
        results.append(("Webhook (Balance)", test_webhook_with_balance()))
        test_api_endpoints()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print("\n" + "=" * 60)
    if all(result[1] for result in results):
        print("✅ All tests passed! Your app is working locally.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    print("=" * 60)

if __name__ == "__main__":
    main()

