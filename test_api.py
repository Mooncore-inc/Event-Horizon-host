#!/usr/bin/env python3
"""
Simple API testing script for Event Horizon Chat
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_health():
    """Test health check endpoint"""
    print("🏥 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_info():
    """Test info endpoint"""
    print("\n📋 Testing info endpoint...")
    try:
        response = requests.get(f"{API_BASE}/system/info")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_key_exchange():
    """Test public key exchange"""
    print("\n🔑 Testing key exchange...")
    
    # Test data
    test_did = "did:example:testuser123"
    test_public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
    
    payload = {
        "did": test_did,
        "public_key": test_public_key
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/keys/exchange",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            # Test retrieving the key
            print("\n🔍 Testing key retrieval...")
            get_response = requests.get(f"{API_BASE}/keys/{test_did}")
            print(f"Get Status: {get_response.status_code}")
            print(f"Get Response: {json.dumps(get_response.json(), indent=2)}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_message_send():
    """Test sending a message"""
    print("\n💬 Testing message sending...")
    
    # Test data
    payload = {
        "sender_did": "did:example:sender123",
        "recipient_did": "did:example:recipient456",
        "encrypted_key": "base64_encoded_encrypted_symmetric_key",
        "iv": "base64_encoded_initialization_vector",
        "ciphertext": "base64_encoded_encrypted_message"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/messages/send",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_message_retrieval():
    """Test message retrieval"""
    print("\n📥 Testing message retrieval...")
    
    test_did = "did:example:sender123"
    
    try:
        response = requests.get(f"{API_BASE}/messages/{test_did}?limit=10")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_websocket_status():
    """Test WebSocket connection status"""
    print("\n🌐 Testing WebSocket status...")
    
    try:
        response = requests.get(f"{BASE_URL}/ws/connections/status")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_stats():
    """Test statistics endpoints"""
    print("\n📊 Testing statistics endpoints...")
    
    try:
        # Test system overview
        response = requests.get(f"{API_BASE}/stats/overview")
        print(f"Stats Overview Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Stats: {json.dumps(response.json(), indent=2)}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Event Horizon Chat API Testing")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Info", test_info),
        ("Key Exchange", test_key_exchange),
        ("Message Send", test_message_send),
        ("Message Retrieval", test_message_retrieval),
        ("WebSocket Status", test_websocket_status),
        ("Statistics", test_stats)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the server logs for details.")

if __name__ == "__main__":
    main()
