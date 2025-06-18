#!/usr/bin/env python3
"""
Check what Facebook Pages you already have
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_pages_with_user_token():
    """Check pages using user access token"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if not token:
        print("❌ INSTAGRAM_ACCESS_TOKEN not found in .env")
        return
    
    print("🔍 Checking Facebook Pages you manage...")
    print("=" * 60)
    
    try:
        # First, let's see what we can access
        url = "https://graph.facebook.com/v18.0/me"
        params = {
            "access_token": token,
            "fields": "id,name,accounts"
        }
        
        print("🧪 Testing basic access...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        user_data = response.json()
        
        print(f"✅ Connected as: {user_data.get('name')}")
        print(f"   User ID: {user_data.get('id')}")
        print()
        
        # Try to get pages
        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {
            "access_token": token,
            "fields": "id,name,access_token,category,link,instagram_business_account"
        }
        
        print("📄 Fetching your pages...")
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json()
        
        pages = pages_data.get('data', [])
        
        if pages:
            print(f"✅ Found {len(pages)} Facebook Page(s):")
            print()
            
            for i, page in enumerate(pages, 1):
                print(f"📄 PAGE {i}: {page.get('name')}")
                print(f"   Page ID: {page.get('id')}")
                print(f"   Category: {page.get('category', 'Unknown')}")
                print(f"   URL: {page.get('link', 'Unknown')}")
                
                if 'instagram_business_account' in page:
                    print(f"   ✅ Instagram connected: {page['instagram_business_account']['id']}")
                else:
                    print(f"   ❌ No Instagram connected")
                
                print(f"   Page Token: {page.get('access_token', 'Not available')[:50]}...")
                print("-" * 40)
        else:
            print("❌ No Facebook Pages found")
            print("\nThis could mean:")
            print("1. You don't have any Facebook Pages")
            print("2. Your access token doesn't have 'pages_show_list' permission")
            print("3. You need to grant page permissions to your app")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response:
            error_data = e.response.json() if e.response.headers.get('content-type') == 'application/json' else e.response.text
            print(f"   Response: {error_data}")
            
            if 'OAuthException' in str(error_data):
                print("\n💡 This looks like a permissions issue!")
                print("   Your token might be missing 'pages_show_list' permission")
                print("   Go to Graph API Explorer and add this permission")

def check_permissions():
    """Check what permissions your token has"""
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if not token:
        return
    
    print("\n🔐 Checking your token permissions...")
    print("=" * 60)
    
    try:
        url = "https://graph.facebook.com/v18.0/me/permissions"
        params = {"access_token": token}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        permissions = data.get('data', [])
        granted = [p['permission'] for p in permissions if p.get('status') == 'granted']
        declined = [p['permission'] for p in permissions if p.get('status') == 'declined']
        
        print("✅ Granted permissions:")
        for perm in granted:
            print(f"   • {perm}")
        
        if declined:
            print("\n❌ Declined permissions:")
            for perm in declined:
                print(f"   • {perm}")
        
        # Check if we have the required permissions
        required = ['pages_show_list', 'pages_manage_posts', 'instagram_basic', 'instagram_content_publish']
        missing = [p for p in required if p not in granted]
        
        if missing:
            print(f"\n⚠️  Missing required permissions:")
            for perm in missing:
                print(f"   • {perm}")
            print("\n💡 To fix this:")
            print("   1. Go to https://developers.facebook.com/tools/explorer/")
            print("   2. Add the missing permissions")
            print("   3. Generate a new access token")
        else:
            print("\n🎉 All required permissions are granted!")
            
    except Exception as e:
        print(f"❌ Error checking permissions: {e}")

def main():
    print("📄 CHECKING YOUR FACEBOOK PAGES")
    print("=" * 60)
    
    check_pages_with_user_token()
    check_permissions()
    
    print("\n" + "=" * 60)
    print("💡 NEXT STEPS")
    print("=" * 60)
    print("If you saw pages above:")
    print("• Connect Instagram to one of them at business.facebook.com")
    print("• Run 'python get_remaining_ids.py' again")
    print()
    print("If no pages found:")
    print("• Check if you need 'pages_show_list' permission")
    print("• Or create a new page at facebook.com/pages/create")

if __name__ == "__main__":
    main()