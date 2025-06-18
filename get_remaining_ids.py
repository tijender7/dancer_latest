#!/usr/bin/env python3
"""
Get remaining IDs using your long-lived token
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_pages_and_instagram_info():
    """Get Facebook Pages and Instagram Business Account info"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if not token:
        print("❌ INSTAGRAM_ACCESS_TOKEN not found in .env")
        return
    
    print("🔍 Fetching your Facebook Pages and Instagram info...")
    print("=" * 60)
    
    try:
        # Get user's pages
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            "access_token": token,
            "fields": "name,id,access_token,instagram_business_account,category,fan_count"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        pages = data.get('data', [])
        
        if not pages:
            print("❌ No Facebook Pages found")
            print("   You need to create a Facebook Page first")
            return
        
        print(f"📄 Found {len(pages)} Facebook Page(s):")
        print()
        
        for i, page in enumerate(pages, 1):
            print(f"📄 PAGE {i}: {page.get('name', 'Unknown')}")
            print(f"   Facebook Page ID: {page.get('id')}")
            print(f"   Category: {page.get('category', 'Unknown')}")
            print(f"   Followers: {page.get('fan_count', 'Unknown')}")
            print(f"   Page Access Token: {page.get('access_token', 'Not available')[:50]}...")
            
            # Check for Instagram Business Account
            if 'instagram_business_account' in page:
                instagram_id = page['instagram_business_account']['id']
                print(f"   ✅ Instagram Business Account ID: {instagram_id}")
                
                # Get Instagram account details
                insta_info = get_instagram_details(instagram_id, token)
                if insta_info:
                    print(f"   📱 Instagram Username: @{insta_info.get('username', 'Unknown')}")
                    print(f"   📱 Instagram Account Type: {insta_info.get('account_type', 'Unknown')}")
                
                print()
                print("💾 ADD THESE TO YOUR .env FILE:")
                print(f"INSTAGRAM_USER_ID={instagram_id}")
                print(f"FACEBOOK_PAGE_ID={page.get('id')}")
                print(f"FACEBOOK_PAGE_ACCESS_TOKEN={page.get('access_token', '')}")
                print()
                
            else:
                print("   ❌ No Instagram Business Account connected")
                print("   ⚠️  You need to connect your Instagram Business account to this Facebook Page")
                print("   📋 Steps:")
                print("      1. Go to https://business.facebook.com")
                print("      2. Select this Facebook Page")
                print("      3. Settings > Accounts > Instagram")
                print("      4. Connect your Instagram Business account")
            
            print("-" * 60)
        
        if any('instagram_business_account' in page for page in pages):
            print("🎉 SUCCESS! Copy the values above to your .env file")
        else:
            print("⚠️  No Instagram Business accounts found")
            print("   Connect your Instagram account to a Facebook Page first")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching pages: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def get_instagram_details(instagram_id, token):
    """Get Instagram account details"""
    try:
        url = f"https://graph.facebook.com/v18.0/{instagram_id}"
        params = {
            "access_token": token,
            "fields": "username,account_type,name,profile_picture_url"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"   ⚠️  Could not get Instagram details: {e}")
        return None

def test_token_first():
    """Test if the token works"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if not token:
        print("❌ INSTAGRAM_ACCESS_TOKEN not found in .env")
        return False
    
    print("🧪 Testing your access token...")
    
    try:
        url = "https://graph.facebook.com/v18.0/me"
        params = {"access_token": token}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Token is valid!")
        print(f"   Connected to: {data.get('name', 'Unknown')}")
        print(f"   User ID: {data.get('id', 'Unknown')}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Token test failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return False

def main():
    print("🔐 GETTING REMAINING IDS FOR SOCIAL MEDIA POSTING")
    print("=" * 60)
    
    if test_token_first():
        print()
        get_pages_and_instagram_info()
    else:
        print("\n❌ Token is invalid. Please get a new one:")
        print("   1. Go to https://developers.facebook.com/tools/explorer/")
        print("   2. Generate a new access token")
        print("   3. Make it long-lived using Token Debugger")
        print("   4. Update your .env file")

if __name__ == "__main__":
    main()