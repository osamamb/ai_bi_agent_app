#!/usr/bin/env python3
"""
Debug script to test Genie connection with actual configuration
"""

import os
import requests
import json

def test_genie_connection():
    """Test Genie connection with current environment variables"""
    
    print("🔍 Genie Connection Diagnostic")
    print("=" * 50)
    
    # Get environment variables
    host = os.getenv("DATABRICKS_HOST", "")
    token = os.getenv("DATABRICKS_TOKEN", "")
    space_id = os.getenv("GENIE_SPACE_ID", "")
    
    print(f"📋 Configuration:")
    print(f"   DATABRICKS_HOST: {host}")
    print(f"   DATABRICKS_TOKEN: {'*' * 10 + token[-4:] if len(token) > 4 else 'NOT_SET'}")
    print(f"   GENIE_SPACE_ID: {space_id}")
    print()
    
    # Check for missing configuration
    if not host:
        print("❌ DATABRICKS_HOST is not set")
        return False
    
    if not token:
        print("❌ DATABRICKS_TOKEN is not set")
        return False
        
    if not space_id:
        print("❌ GENIE_SPACE_ID is not set")
        return False
    
    # Check for placeholder values
    if token == "YOUR_DATABRICKS_TOKEN_HERE":
        print("❌ DATABRICKS_TOKEN is still set to placeholder value")
        return False
    
    if space_id == "YOUR_GENIE_SPACE_ID_HERE":
        print("❌ GENIE_SPACE_ID is still set to placeholder value")
        return False
    
    print("✅ All configuration values are set")
    print()
    
    # Test connection
    print("🌐 Testing Genie API connection...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Try different API endpoints
    endpoints_to_try = [
        f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}/start-conversation",
        f"{host.rstrip('/')}/api/2.1/genie/spaces/{space_id}/start-conversation",
        f"{host.rstrip('/')}/api/2.0/genie/spaces/{space_id}/conversations",
        f"{host.rstrip('/')}/api/2.1/genie/spaces/{space_id}/conversations"
    ]
    
    payload = {"content": "Test connection"}
    
    for i, url in enumerate(endpoints_to_try, 1):
        print(f"   {i}. Testing: {url}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"      Status: {response.status_code}")
            
            if response.status_code == 200:
                print("      ✅ SUCCESS! Connection working")
                result = response.json()
                print(f"      Response keys: {list(result.keys())}")
                return True
            elif response.status_code == 401:
                print("      ❌ Authentication failed - check your token")
                print(f"      Response: {response.text[:200]}")
            elif response.status_code == 403:
                print("      ❌ Access forbidden - check permissions")
                print(f"      Response: {response.text[:200]}")
            elif response.status_code == 404:
                print("      ❌ Not found - check space ID")
                print(f"      Response: {response.text[:200]}")
            else:
                print(f"      ❌ HTTP {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("      ❌ Request timeout")
        except requests.exceptions.ConnectionError:
            print(f"      ❌ Connection error - check if {host} is accessible")
        except Exception as e:
            print(f"      ❌ Error: {str(e)}")
        
        print()
    
    print("❌ All endpoints failed")
    return False

if __name__ == "__main__":
    success = test_genie_connection()
    
    if not success:
        print("\n💡 Troubleshooting Tips:")
        print("1. Verify your DATABRICKS_TOKEN has the correct permissions")
        print("2. Check if the Genie space ID exists and you have access")
        print("3. Ensure your Databricks workspace URL is correct")
        print("4. Try generating a new personal access token")
