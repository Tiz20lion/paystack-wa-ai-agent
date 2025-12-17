#!/usr/bin/env python3
"""
OpenRouter API Integration Test
Tests the OpenRouter API connectivity and AI functionality.
"""

import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openrouter_connection():
    """Test OpenRouter API connection."""
    print("🤖 Testing OpenRouter API Integration")
    print("="*50)
    
    # Get configuration
    api_key = os.getenv('OPENROUTER_API_KEY', '')
    model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    site_url = os.getenv('OPENROUTER_SITE_URL', '')
    site_name = os.getenv('OPENROUTER_SITE_NAME', 'Paystack WhatsApp Agent')
    
    # Check configuration
    print(f"🔑 API Key: {'✅ Configured' if api_key and api_key != '' else '❌ Not configured'}")
    print(f"🎯 Model: {model}")
    print(f"🌐 Site URL: {site_url if site_url else 'Not configured'}")
    print(f"🏷️  Site Name: {site_name}")
    
    if not api_key:
        print("\n⚠️  OpenRouter API key not configured!")
        print("To test OpenRouter integration:")
        print("1. Get an API key from https://openrouter.ai/keys")
        print("2. Add it to your .env file: OPENROUTER_API_KEY=your_key_here")
        print("3. Run this test again")
        return False
    
    # Test API connection
    print(f"\n🔄 Testing API connection...")
    
    try:
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Add optional headers
        if site_url:
            headers["HTTP-Referer"] = site_url
        
        if site_name:
            headers["X-Title"] = site_name
        
        # Test message
        test_message = "Hello! I'm testing the OpenRouter API integration for a Paystack banking assistant. Please respond with a brief greeting."
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful banking assistant for Paystack transactions. Keep responses concise and professional."
                },
                {
                    "role": "user",
                    "content": test_message
                }
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }
        
        print(f"📨 Sending test message: '{test_message[:50]}...'")
        
        # Make the API request
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        print(f"📈 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                ai_response = result['choices'][0]['message']['content']
                print(f"✅ API Response: {ai_response}")
                
                # Check usage information
                if 'usage' in result:
                    usage = result['usage']
                    print(f"📊 Token Usage: {usage.get('total_tokens', 'N/A')} tokens")
                    print(f"   - Prompt: {usage.get('prompt_tokens', 'N/A')}")
                    print(f"   - Completion: {usage.get('completion_tokens', 'N/A')}")
                
                print("\n🎉 OpenRouter API integration successful!")
                return True
            else:
                print("❌ Invalid response format from OpenRouter")
                return False
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📝 Error details: {error_data}")
            except:
                print(f"📝 Error response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - check your internet connection")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_banking_conversation():
    """Test banking-specific conversation."""
    print(f"\n💼 Testing Banking Conversation")
    print("="*50)
    
    api_key = os.getenv('OPENROUTER_API_KEY', '')
    model = os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    
    if not api_key:
        print("⚠️  Skipping banking conversation test - API key not configured")
        return False
    
    # Banking-specific test messages
    test_messages = [
        "I want to check my account balance",
        "How do I transfer money to another account?",
        "What banks are supported by Paystack?",
        "Can you help me with a transfer to Access Bank?"
    ]
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        system_prompt = """You are a helpful banking assistant for Paystack transactions. 
        You can help users with:
        - Checking account balances
        - Making transfers to other accounts
        - Resolving bank account details
        - Viewing transaction history
        - General banking questions
        
        Always be polite, secure, and helpful. Keep responses concise and actionable."""
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🔍 Test {i}: '{message}'")
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                print(f"✅ Response: {ai_response}")
            else:
                print(f"❌ Request failed: {response.status_code}")
                break
        
        print("\n🎉 Banking conversation tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Banking conversation test failed: {e}")
        return False

def show_openrouter_setup_guide():
    """Show setup guide for OpenRouter."""
    print("\n" + "="*60)
    print("📚 OpenRouter Setup Guide")
    print("="*60)
    
    print("\n1. 🔑 Get an OpenRouter API Key:")
    print("   - Visit https://openrouter.ai/keys")
    print("   - Sign up for a free account")
    print("   - Create a new API key")
    
    print("\n2. 📝 Update your .env file:")
    print("   OPENROUTER_API_KEY=your_api_key_here")
    print("   OPENROUTER_MODEL=openai/gpt-4o-mini")
    print("   OPENROUTER_SITE_URL=https://your-site.com")
    print("   OPENROUTER_SITE_NAME=Paystack WhatsApp Agent")
    
    print("\n3. 🎯 Available Models:")
    print("   - openai/gpt-4o-mini (fast, affordable)")
    print("   - openai/gpt-4o (more capable)")
    print("   - anthropic/claude-3.5-sonnet (excellent reasoning)")
    print("   - meta-llama/llama-3.1-8b-instruct (open source)")
    
    print("\n4. 💰 Pricing Benefits:")
    print("   - Often 10-50% cheaper than direct OpenAI API")
    print("   - Access to multiple AI providers")
    print("   - No need for separate API keys")
    print("   - Unified interface for all models")
    
    print("\n5. 🔄 Test the Integration:")
    print("   python test_openrouter.py")
    
    print("\n6. 🚀 Run the Full App:")
    print("   python cli_app.py")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    print("🚀 OpenRouter Integration Test Suite")
    print("="*60)
    
    # Test basic connection
    connection_success = test_openrouter_connection()
    
    # Test banking conversation if basic connection works
    if connection_success:
        test_banking_conversation()
    
    # Show setup guide if needed
    if not connection_success:
        show_openrouter_setup_guide()
    
    print("\n✨ OpenRouter test completed!") 