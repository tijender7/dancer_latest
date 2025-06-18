#!/usr/bin/env python3
"""
Facebook & Instagram API Setup Helper
Step-by-step guide to get all required credentials
"""
import os
import requests
from dotenv import load_dotenv

def test_token(token, token_type="Unknown"):
    """Test if a token is valid"""
    url = f"https://graph.facebook.com/v18.0/me"
    params = {"access_token": token}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {token_type} Token is VALID")
            print(f"   User: {data.get('name', 'Unknown')}")
            print(f"   ID: {data.get('id', 'Unknown')}")
            return True
        else:
            print(f"❌ {token_type} Token is INVALID")
            print(f"   Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ {token_type} Token test failed: {e}")
        return False

def get_pages(token):
    """Get Facebook pages"""
    url = f"https://graph.facebook.com/v18.0/me/accounts"
    params = {
        "access_token": token,
        "fields": "name,id,access_token,instagram_business_account"
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            print(f"❌ Error getting pages: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting pages: {e}")
        return []

def main():
    print("🔧 FACEBOOK & INSTAGRAM API SETUP HELPER")
    print("=" * 60)
    
    load_dotenv()
    current_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    if current_token:
        print(f"📱 Found existing token in .env file")
        print(f"🧪 Testing current token...")
        
        if test_token(current_token, "Current"):
            print("\n📄 Getting your Facebook Pages...")
            pages = get_pages(current_token)
            
            if pages:
                print(f"\n📋 Found {len(pages)} Facebook Page(s):")
                for i, page in enumerate(pages, 1):
                    print(f"\n{i}. Page Name: {page.get('name')}")
                    print(f"   Page ID: {page.get('id')}")
                    
                    if 'instagram_business_account' in page:
                        insta_id = page['instagram_business_account']['id']
                        print(f"   ✅ Instagram Business Account: {insta_id}")
                        
                        print(f"\n💾 ADD TO YOUR .env FILE:")
                        print(f"INSTAGRAM_USER_ID={insta_id}")
                        print(f"FACEBOOK_PAGE_ID={page.get('id')}")
                        print(f"FACEBOOK_PAGE_ACCESS_TOKEN={page.get('access_token', 'Not available')}")
                    else:
                        print(f"   ❌ No Instagram Business Account connected")
                        print(f"       You need to connect Instagram to this Facebook Page")
                
                return
            else:
                print("❌ No Facebook Pages found")
    
    print("\n" + "="*60)
    print("🚨 TOKEN EXPIRED OR INVALID - MANUAL SETUP REQUIRED")
    print("="*60)
    
    print("\n📋 STEP-BY-STEP SETUP GUIDE:")
    print("\n1️⃣ **Go to Facebook Developer Console:**")
    print("   https://developers.facebook.com/")
    
    print("\n2️⃣ **Create/Select App:**")
    print("   - Create new app or select existing")
    print("   - Choose 'Business' type")
    
    print("\n3️⃣ **Add Products:**")
    print("   - Facebook Login")
    print("   - Instagram Basic Display")  
    print("   - Instagram Graph API")
    print("   - Facebook Pages API")
    
    print("\n4️⃣ **Generate Access Token:**")
    print("   - Go to Tools > Graph API Explorer")
    print("   - Select your app")
    print("   - Request these permissions:")
    print("     • pages_show_list")
    print("     • pages_manage_posts")
    print("     • instagram_basic")
    print("     • instagram_content_publish")
    print("     • business_management")
    
    print("\n5️⃣ **Get Long-Lived Token:**")
    print("   - Copy the short-lived token")
    print("   - Use Graph API Explorer or run:")
    print("   curl -i -X GET \"https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN\"")
    
    print("\n6️⃣ **Connect Instagram to Facebook Page:**")
    print("   - Go to business.facebook.com")
    print("   - Select your Facebook Page")
    print("   - Settings > Instagram > Connect Account")
    print("   - Make sure it's a Business/Creator account")
    
    print("\n7️⃣ **Update .env file with:**")
    print("   INSTAGRAM_ACCESS_TOKEN=your_long_lived_token")
    print("   INSTAGRAM_USER_ID=your_instagram_business_id")
    print("   FACEBOOK_PAGE_ACCESS_TOKEN=your_page_token")
    print("   FACEBOOK_PAGE_ID=your_facebook_page_id")
    
    print("\n8️⃣ **Test Setup:**")
    print("   python setup_facebook_instagram_api.py")
    
    print("\n" + "="*60)
    print("💡 ALTERNATIVE: Use Instagram Basic API Only")
    print("="*60)
    print("Your existing Instagram username/password works!")
    print("Just run: python post_upscaled_videos.py")
    print("It will use basic Instagram API and skip Facebook")

if __name__ == "__main__":
    main()