#!/usr/bin/env python3
"""
Find Instagram Business User ID from Facebook Pages
"""

import requests
import json

# Your credentials
ACCESS_TOKEN = "EAAWEgplFszMBO302WnZClu7XP3YL0qZCXP9tJUqlEMA7A7hcqH2ntyipFEmO7v3VhKQvRU2PKbeeUSHt83GO8RABQLLZAkvo3zzOw2Ik5rcw2oobiaONdlGZBMjZB3LJZBWHXQM7ZAC05rpHBqYYo7SRe1rRZA42P5qVoos5uosZAcQbcRwBAnM9QXu4qZATnwnfTdxU4M5PCTAZBCifOXKGezaQIAyZBQtWcFoZD"

def find_instagram_accounts():
    """Find all Instagram accounts connected to your Facebook pages."""
    
    print("🔍 Searching for Instagram Business accounts...")
    
    # Step 1: Get all pages you manage
    url = "https://graph.facebook.com/v18.0/me/accounts"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "name,id,instagram_business_account"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"\n📄 Found {len(data.get('data', []))} Facebook page(s):")
        
        instagram_accounts = []
        
        for page in data.get('data', []):
            page_name = page.get('name', 'Unknown')
            page_id = page.get('id', 'Unknown')
            instagram_account = page.get('instagram_business_account')
            
            print(f"\n📄 Page: {page_name}")
            print(f"   Page ID: {page_id}")
            
            if instagram_account:
                instagram_id = instagram_account.get('id')
                print(f"   ✅ Instagram Business Account ID: {instagram_id}")
                instagram_accounts.append({
                    'page_name': page_name,
                    'page_id': page_id,
                    'instagram_id': instagram_id
                })
                
                # Get Instagram account details
                get_instagram_details(instagram_id)
            else:
                print(f"   ❌ No Instagram Business account connected")
        
        return instagram_accounts
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting pages: {e}")
        return []

def get_instagram_details(instagram_id: str):
    """Get details about an Instagram business account."""
    url = f"https://graph.facebook.com/v18.0/{instagram_id}"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "account_type,username,name,profile_picture_url,followers_count,media_count"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"      📱 Instagram Username: @{data.get('username', 'N/A')}")
        print(f"      👤 Account Name: {data.get('name', 'N/A')}")
        print(f"      🏢 Account Type: {data.get('account_type', 'N/A')}")
        print(f"      👥 Followers: {data.get('followers_count', 'N/A')}")
        print(f"      📸 Media Count: {data.get('media_count', 'N/A')}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"      ❌ Error getting Instagram details: {e}")
        return None

def test_instagram_permissions(instagram_id: str):
    """Test if we have the required permissions for posting."""
    print(f"\n🧪 Testing permissions for Instagram ID: {instagram_id}")
    
    # Test basic read permission
    url = f"https://graph.facebook.com/v18.0/{instagram_id}/media"
    params = {
        "access_token": ACCESS_TOKEN,
        "limit": 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        print("   ✅ Basic read permission: OK")
        
        # Test if we can create containers (needed for posting)
        test_url = f"https://graph.facebook.com/v18.0/{instagram_id}"
        test_params = {
            "access_token": ACCESS_TOKEN,
            "fields": "account_type"
        }
        
        test_response = requests.get(test_url, params=test_params)
        test_response.raise_for_status()
        
        account_type = test_response.json().get('account_type')
        if account_type == 'BUSINESS':
            print("   ✅ Account type: BUSINESS (suitable for posting)")
            return True
        else:
            print(f"   ⚠️ Account type: {account_type} (may need BUSINESS account)")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Permission test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 Instagram Business Account Finder")
    print("=" * 60)
    
    # Find Instagram accounts
    instagram_accounts = find_instagram_accounts()
    
    if not instagram_accounts:
        print("\n❌ No Instagram Business accounts found!")
        print("\n💡 Setup steps:")
        print("   1. Convert your Instagram to Business account")
        print("   2. Create a Facebook Page")
        print("   3. Connect Instagram to the Facebook Page")
        print("   4. Make sure you're an admin of the page")
        return
    
    print(f"\n✅ Found {len(instagram_accounts)} Instagram Business account(s)!")
    
    # Test permissions for each account
    for account in instagram_accounts:
        instagram_id = account['instagram_id']
        page_name = account['page_name']
        
        print(f"\n📱 Testing account for page '{page_name}':")
        can_post = test_instagram_permissions(instagram_id)
        
        if can_post:
            print(f"\n🎉 READY FOR AUTOMATION!")
            print(f"   Use this Instagram User ID: {instagram_id}")
            print(f"   Page ID: {account['page_id']}")
            
            # Save config
            config = {
                "access_token": ACCESS_TOKEN,
                "instagram_user_id": instagram_id,
                "page_id": account['page_id'],
                "app_id": "1553071335650099",
                "app_secret": "5e5b9147aad3c348e1834c07d802d8d8",
                "api_version": "v18.0",
                "page_name": page_name,
                "setup_date": "2024-06-11"
            }
            
            with open("instagram_config_temp.json", "w") as f:
                json.dump(config, f, indent=2)
            
            print(f"   💾 Temporary config saved to: instagram_config_temp.json")
            break

if __name__ == "__main__":
    main()