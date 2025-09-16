#!/usr/bin/env python3
"""
Genie Connection Diagnostic Tool
Helps diagnose timeout and connection issues with Databricks Genie
"""

import os
import sys
import requests
import time
from typing import Dict, Any, Optional

def test_genie_connection():
    """Test Genie connection step by step."""
    print("🔍 Genie Connection Diagnostic Tool")
    print("=" * 50)
    
    # Get configuration
    host = os.getenv("DATABRICKS_HOST", "").rstrip('/')
    token = os.getenv("DATABRICKS_TOKEN", "")
    space_id = os.getenv("GENIE_SPACE_ID", "")
    
    print(f"📋 Configuration:")
    print(f"   Host: {host}")
    print(f"   Token: {token[:10]}{'*' * 10}{token[-4:] if len(token) > 14 else ''}")
    print(f"   Space ID: {space_id}")
    print()
    
    if not all([host, token, space_id]):
        print("❌ Missing required configuration!")
        print("   Set DATABRICKS_HOST, DATABRICKS_TOKEN, and GENIE_SPACE_ID")
        return False
    
    if token == "YOUR_DATABRICKS_TOKEN_HERE":
        print("❌ Token is still placeholder value!")
        print("   Update app.yaml with your actual Databricks personal access token")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Basic connectivity
    print("🧪 Test 1: Basic Databricks connectivity...")
    try:
        response = requests.get(f"{host}/api/2.0/clusters/list", headers=headers, timeout=10)
        if response.status_code == 200:
            print("   ✅ Basic connectivity: OK")
        elif response.status_code == 401:
            print("   ❌ Authentication failed - check your token")
            return False
        elif response.status_code == 403:
            print("   ❌ Access forbidden - check token permissions")
            return False
        else:
            print(f"   ⚠️ Unexpected response: {response.status_code}")
    except requests.exceptions.Timeout:
        print("   ❌ Connection timeout - check network/firewall")
        return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    # Test 2: Genie space access
    print("🧪 Test 2: Genie space access...")
    try:
        response = requests.get(f"{host}/api/2.0/genie/spaces/{space_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            space_data = response.json()
            print(f"   ✅ Genie space access: OK")
            print(f"   📊 Space name: {space_data.get('display_name', 'Unknown')}")
        elif response.status_code == 404:
            print(f"   ❌ Genie space not found: {space_id}")
            print("   Check if the space ID is correct and you have access")
            return False
        else:
            print(f"   ❌ Space access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Space access error: {e}")
        return False
    
    # Test 3: Start conversation (this is where timeouts usually happen)
    print("🧪 Test 3: Start Genie conversation...")
    try:
        payload = {"content": "Hello, can you help me?"}
        start_time = time.time()
        
        response = requests.post(
            f"{host}/api/2.0/genie/spaces/{space_id}/start-conversation",
            headers=headers,
            json=payload,
            timeout=30  # 30 second timeout
        )
        
        elapsed = time.time() - start_time
        print(f"   ⏱️ Request took: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            conv_data = response.json()
            conv_id = conv_data.get("conversation_id")
            msg_id = conv_data.get("message_id")
            print(f"   ✅ Conversation started: OK")
            print(f"   🆔 Conversation ID: {conv_id}")
            print(f"   📨 Message ID: {msg_id}")
            
            # Test 4: Wait for response (this is where "Query timed out" happens)
            print("🧪 Test 4: Wait for Genie response...")
            return test_genie_response(host, headers, space_id, conv_id, msg_id)
            
        else:
            print(f"   ❌ Failed to start conversation: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Conversation start timed out after 30 seconds")
        print("   This suggests Genie service is overloaded or slow")
        return False
    except Exception as e:
        print(f"   ❌ Conversation start error: {e}")
        return False

def test_genie_response(host: str, headers: Dict[str, str], space_id: str, conv_id: str, msg_id: str) -> bool:
    """Test waiting for Genie response."""
    max_wait = 30
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            url = f"{host}/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                message_data = response.json()
                status = message_data.get("status", "UNKNOWN")
                
                print(f"   📊 Message status: {status}")
                
                if status == "COMPLETED":
                    content = message_data.get("content", "")
                    print(f"   ✅ Genie response received!")
                    print(f"   📝 Response: {content[:100]}...")
                    return True
                elif status == "FAILED":
                    error = message_data.get("error", "Unknown error")
                    print(f"   ❌ Genie processing failed: {error}")
                    return False
                else:
                    # Still processing, wait a bit
                    time.sleep(2)
            else:
                print(f"   ⚠️ Status check failed: {response.status_code}")
                time.sleep(2)
                
        except Exception as e:
            print(f"   ⚠️ Status check error: {e}")
            time.sleep(2)
    
    elapsed = time.time() - start_time
    print(f"   ❌ Genie response timed out after {elapsed:.1f} seconds")
    print("   💡 This indicates:")
    print("      - Genie is processing but taking too long")
    print("      - Try simpler questions")
    print("      - Check if your data sources are accessible")
    print("      - Consider increasing timeout in production")
    return False

if __name__ == "__main__":
    print("Starting Genie diagnostic...")
    print("Make sure to set environment variables:")
    print("export DATABRICKS_HOST='your-workspace-url'")
    print("export DATABRICKS_TOKEN='your-token'") 
    print("export GENIE_SPACE_ID='your-space-id'")
    print()
    
    success = test_genie_connection()
    
    if success:
        print("\n🎉 All tests passed! Genie connection is working.")
        print("💡 If you're still seeing timeouts in the app:")
        print("   1. Try simpler, more specific questions")
        print("   2. Check if your datasets are properly configured in Genie")
        print("   3. Consider increasing timeout values")
    else:
        print("\n❌ Diagnostic found issues. Fix the problems above and try again.")
        
    sys.exit(0 if success else 1)
