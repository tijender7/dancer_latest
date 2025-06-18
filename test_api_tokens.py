#!/usr/bin/env python3
"""
Test Facebook & Instagram API Tokens
Verify all tokens work before using the main posting script
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_instagram_token():
    """Test Instagram Graph API token"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.getenv("INSTAGRAM_USER_ID")
    
    print("🧪 Testing Instagram Graph API...")
    
    if not token:
        print("❌ INSTAGRAM_ACCESS_TOKEN not found in .env")
        return False
    
    if not user_id:
        print("❌ INSTAGRAM_USER_ID not found in .env")
        return False
    
    try:
        # Test token validity
        url = f"https://graph.facebook.com/v18.0/{user_id}"
        params = {
            "access_token": token,
            "fields": "account_type,username,name,profile_picture_url"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Instagram API: Connected successfully!")
            print(f"   Username: @{data.get('username', 'Unknown')}")
            print(f"   Account Type: {data.get('account_type', 'Unknown')}")
            print(f"   Name: {data.get('name', 'Unknown')}")
            
            if data.get('account_type') != 'BUSINESS':
                print("⚠️  WARNING: Account should be BUSINESS type for posting")
                return False
            
            return True
        else:
            print(f"❌ Instagram API: Failed ({response.status_code})")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Instagram API: Error - {e}")
        return False

def test_facebook_token():
    """Test Facebook Pages API token"""
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    print("\n🧪 Testing Facebook Pages API...")
    
    if not token:
        print("❌ FACEBOOK_PAGE_ACCESS_TOKEN not found in .env")
        return False
    
    if not page_id:
        print("❌ FACEBOOK_PAGE_ID not found in .env")
        return False
    
    try:
        # Test page access
        url = f"https://graph.facebook.com/v18.0/{page_id}"
        params = {
            "access_token": token,
            "fields": "name,category,fan_count,instagram_business_account"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Facebook API: Connected successfully!")
            print(f"   Page Name: {data.get('name', 'Unknown')}")
            print(f"   Category: {data.get('category', 'Unknown')}")
            print(f"   Followers: {data.get('fan_count', 'Unknown')}")
            
            if 'instagram_business_account' in data:
                print(f"   ✅ Instagram Business Account connected")
            else:
                print(f"   ⚠️  No Instagram Business Account connected")
            
            return True
        else:
            print(f"❌ Facebook API: Failed ({response.status_code})")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Facebook API: Error - {e}")
        return False

def test_token_permissions():
    """Test if tokens have required permissions"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if not token:
        return False
    
    print("\n🔐 Testing Token Permissions...")
    
    try:
        url = f"https://graph.facebook.com/v18.0/me/permissions"
        params = {"access_token": token}
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            permissions = [p['permission'] for p in data.get('data', []) if p.get('status') == 'granted']
            
            required_permissions = [
                'pages_show_list',
                'pages_manage_posts',
                'instagram_basic',
                'instagram_content_publish'
            ]
            
            print("📋 Granted Permissions:")
            for perm in permissions:
                print(f"   ✅ {perm}")
            
            missing = [p for p in required_permissions if p not in permissions]
            if missing:
                print("\n❌ Missing Required Permissions:")
                for perm in missing:
                    print(f"   ❌ {perm}")
                return False
            else:
                print("\n✅ All required permissions granted!")
                return True
        else:
            print(f"❌ Permission check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Permission check error: {e}")
        return False

def main():
    print("🧪 API TOKEN TESTING")
    print("=" * 50)
    
    instagram_ok = test_instagram_token()
    facebook_ok = test_facebook_token()
    permissions_ok = test_token_permissions()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    print(f"Instagram API: {'✅ PASS' if instagram_ok else '❌ FAIL'}")
    print(f"Facebook API:  {'✅ PASS' if facebook_ok else '❌ FAIL'}")
    print(f"Permissions:   {'✅ PASS' if permissions_ok else '❌ FAIL'}")
    
    if all([instagram_ok, facebook_ok, permissions_ok]):
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Ready to use: python post_upscaled_videos.py")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("📝 Run: python get_facebook_instagram_tokens.py")
        print("   Follow the setup guide to fix the issues")
    
    print("=" * 50)

if __name__ == "__main__":
    main()