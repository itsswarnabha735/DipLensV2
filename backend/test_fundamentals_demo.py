#!/usr/bin/env python3
"""
Demo test for LLM-Assisted Fundamentals Checklist API.
Tests the /fundamentals/{symbol}/suggestions endpoint.
"""

import sys
import json
import requests
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

def test_fundamentals_suggestions(symbol: str):
    """Test fundamentals suggestions endpoint"""
    
    print(f"🧪 Testing Fundamentals Suggestions API for {symbol}")
    print("=" * 70)
    
    url = f"{API_BASE_URL}/fundamentals/{symbol}/suggestions"
    
    print(f"\n📡 Making request to: {url}")
    print("⏳ This may take 10-30 seconds (LLM + Google Search grounding)...\n")
    
    try:
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ SUCCESS! Received grounded suggestions\n")
            print("=" * 70)
            
            # Display Q1: Dip Cause
            print("\n📊 Q1: Dip Cause")
            print(f"   Recommendation: {data['q1']['rec']}")
            print(f"   Confidence: {data['q1']['confidence']}")
            print(f"   Reasons:")
            for i, reason in enumerate(data['q1']['reasons'], 1):
                print(f"     {i}. {reason}")
            print(f"   Citations: {len(data['q1']['citations'])} sources")
            for i, citation in enumerate(data['q1']['citations'], 1):
                print(f"     [{i}] {citation['title']}")
                print(f"         {citation['url']}")
            
            # Display Q2: Earnings
            print("\n💰 Q2: Earnings Resilience")
            print(f"   Recommendation: {data['q2']['rec']}")
            print(f"   Confidence: {data['q2']['confidence']}")
            print(f"   Reasons:")
            for i, reason in enumerate(data['q2']['reasons'], 1):
                print(f"     {i}. {reason}")
            print(f"   Citations: {len(data['q2']['citations'])} sources")
            
            # Display Q3: Management
            print("\n👔 Q3: Management/Guidance")
            print(f"   Recommendation: {data['q3']['rec']}")
            print(f"   Confidence: {data['q3']['confidence']}")
            print(f"   Reasons:")
            for i, reason in enumerate(data['q3']['reasons'], 1):
                print(f"     {i}. {reason}")
            print(f"   Citations: {len(data['q3']['citations'])} sources")
            
            # Display Q4: Support
            print("\n📈 Q4: Support Level")
            print(f"   Recommendation: {data['q4']['rec']}")
            print(f"   Confidence: {data['q4']['confidence']}")
            print(f"   Reasons:")
            for i, reason in enumerate(data['q4']['reasons'], 1):
                print(f"     {i}. {reason}")
            print(f"   Citations: {len(data['q4']['citations'])} sources")
            
            # Display Summary
            print("\n📝 LLM Summary:")
            print(f"   {data['summary']}")
            
            # Metadata
            print("\n🔧 Metadata:")
            print(f"   Generated at: {data['generated_at']}")
            print(f"   Model version: {data['model_version']}")
            
            # Save full response
            output_file = f"fundamentals_demo_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: {output_file}")
            
            return True
            
        elif response.status_code == 503:
            print(f"❌ Error 503: LLM service unavailable")
            print(f"   This usually means GEMINI_API_KEY is not configured.")
            print(f"   Please set it in backend/.env file")
            return False
            
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 60 seconds")
        print("   LLM generation may be taking longer than expected")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection error")
        print("   Make sure the backend server is running:")
        print("   cd backend && ./venv/bin/uvicorn app.main:app --reload")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    # Test with AXISBANK.NS (Indian stock)
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AXISBANK.NS"
    
    print("\n" + "=" * 70)
    print("  LLM-Assisted Fundamentals Checklist - Demo Test")
    print("=" * 70)
    print(f"\n🎯 Symbol: {symbol}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    success = test_fundamentals_suggestions(symbol)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Demo test completed successfully!")
    else:
        print("❌ Demo test failed - see errors above")
    print("=" * 70 + "\n")
    
    sys.exit(0 if success else 1)
