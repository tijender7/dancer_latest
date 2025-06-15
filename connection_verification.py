#!/usr/bin/env python3
"""
Simple debug test for Instagram connection
"""

import requests
import json

# Your credentials
ACCESS_TOKEN = "EAAWEgplFszMBO302WnZClu7XP3YL0qZCXP9tJUqlEMA7A7hcqH2ntyipFEmO7v3VhKQvRU2PKbeeUSHt83GO8RABQLLZAkvo3zzOw2Ik5rcw2oobiaONdlGZBMjZB3LJZBWHXQM7ZAC05rpHBqYYo7SRe1rRZA42P5qVoos5uosZAcQbcRwBAnM9QXu4qZATnwnfTdxU4M5PCTAZBCifOXKGezaQIAyZBQtWcFoZD"

def main():
    print("=" * 50)
    print("🧪 Simple Instagram Connection Debug")
    print("=" * 50)
    
    try:
        # Test 1: Basic API connectivity
        print("1️⃣ Testing basic API connectivity...")
        url = "https://graph.facebook.com/v18.0/me"
        params = {"access_token": ACCESS_TOKEN}
        
        response = requests.get(url, params=params)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Connected as: {data.get('name', 'Unknown')}")
            print(f"   ✅ User ID: {data.get('id', 'Unknown')}")
        else:
            print(f"   ❌ API Error: {response.text}")
            return
        
        # Test 2: Check pages
        print("\n2️⃣ Checking Facebook pages...")
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            "access_token": ACCESS_TOKEN,
            "fields": "name,id,instagram_business_account"
        }
        
        response = requests.get(url, params=params)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get('data', [])
            print(f"   ✅ Found {len(pages)} page(s)")
            
            for i, page in enumerate(pages, 1):
                page_name = page.get('name', 'Unknown')
                page_id = page.get('id', 'Unknown')
                instagram_account = page.get('instagram_business_account')
                
                print(f"\n   📄 Page {i}: {page_name}")
                print(f"      ID: {page_id}")
                
                if instagram_account:
                    instagram_id = instagram_account.get('id')
                    print(f"      ✅ Instagram ID: {instagram_id}")
                    
                    # Test Instagram account
                    print("      🧪 Testing Instagram account...")
                    test_instagram(instagram_id)
                    
                    # Save config
                    save_config(instagram_id, page_id, page_name)
                    return
                else:
                    print(f"      ❌ No Instagram connected")
            
            if not any(page.get('instagram_business_account') for page in pages):
                print(f"\n⚠️  No Instagram accounts connected to any pages.")
                print(f"   📱 Please connect Instagram to 'Dance Content Creator AI' page")
                
        else:
            print(f"   ❌ Pages Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Script Error: {e}")
        import traceback
        traceback.print_exc()

def test_instagram(instagram_id):
    """Test Instagram account details."""
    try:
        url = f"https://graph.facebook.com/v18.0/{instagram_id}"
        params = {
            "access_token": ACCESS_TOKEN,
            "fields": "account_type,username,name"
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"         📱 Username: @{data.get('username', 'N/A')}")
            print(f"         🏢 Type: {data.get('account_type', 'N/A')}")
            print(f"         👤 Name: {data.get('name', 'N/A')}")
            
            if data.get('account_type') == 'BUSINESS':
                print(f"         ✅ Perfect! Ready for automation")
            else:
                print(f"         ⚠️  Should be BUSINESS type")
        else:
            print(f"         ❌ Instagram test failed: {response.text}")
            
    except Exception as e:
        print(f"         ❌ Instagram test error: {e}")

def save_config(instagram_id, page_id, page_name):
    """Save working configuration."""
    config = {
        "instagram_user_id": instagram_id,
        "page_id": page_id,
        "page_name": page_name,
        "access_token": ACCESS_TOKEN,
        "app_id": "1553071335650099",
        "app_secret": "5e5b9147aad3c348e1834c07d802d8d8",
        "api_version": "v18.0",
        "status": "ready_for_automation",
        "test_date": "2024-06-11"
    }
    
    try:
        with open("instagram_config_working.json", "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n💾 Configuration saved to: instagram_config_working.json")
        print(f"🎉 Instagram automation is ready!")
        
    except Exception as e:
        print(f"❌ Failed to save config: {e}")

if __name__ == "__main__":
    main()