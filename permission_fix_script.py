#!/usr/bin/env python3
"""
Fix access token permissions for Instagram Graph API
"""

import requests
import json
import webbrowser
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment variables
APP_ID = os.getenv("INSTAGRAM_APP_ID")
APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
CURRENT_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# Validate required environment variables
required_vars = {
    "INSTAGRAM_APP_ID": APP_ID,
    "INSTAGRAM_APP_SECRET": APP_SECRET,
    "INSTAGRAM_ACCESS_TOKEN": CURRENT_TOKEN
}

missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]
if missing_vars:
    print("ERROR: Missing required environment variables:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease add these to your .env file")
    exit(1)

def check_current_permissions():
    """Check what permissions the current token has."""
    print("🔍 Checking current token permissions...")
    
    url = "https://graph.facebook.com/v18.0/me/permissions"
    params = {"access_token": CURRENT_TOKEN}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        granted_permissions = []
        declined_permissions = []
        
        for perm in data.get('data', []):
            if perm.get('status') == 'granted':
                granted_permissions.append(perm.get('permission'))
            else:
                declined_permissions.append(perm.get('permission'))
        
        print(f"✅ Granted permissions: {', '.join(granted_permissions)}")
        if declined_permissions:
            print(f"❌ Declined permissions: {', '.join(declined_permissions)}")
        
        # Check for required permissions
        required_perms = [
            'pages_read_engagement',
            'pages_show_list', 
            'instagram_basic',
            'instagram_content_publish',
            'business_management'
        ]
        
        missing_perms = [p for p in required_perms if p not in granted_permissions]
        
        if missing_perms:
            print(f"⚠️ Missing required permissions: {', '.join(missing_perms)}")
            return False, missing_perms
        else:
            print("✅ All required permissions granted!")
            return True, []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error checking permissions: {e}")
        return False, []

def generate_auth_url():
    """Generate Facebook OAuth URL with required permissions."""
    
    # Required permissions for Instagram Graph API
    required_permissions = [
        'pages_read_engagement',
        'pages_show_list',
        'pages_manage_posts',
        'instagram_basic', 
        'instagram_content_publish',
        'business_management'
    ]
    
    scope = ','.join(required_permissions)
    redirect_uri = 'https://localhost/'
    
    auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth?"
        f"client_id={APP_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={scope}&"
        f"response_type=code"
    )
    
    print("🔗 Opening Facebook OAuth authorization...")
    print("📋 Required permissions:")
    for perm in required_permissions:
        print(f"   • {perm}")
    
    print(f"\n🌐 Authorization URL: {auth_url}")
    
    try:
        webbrowser.open(auth_url)
        print("✅ Browser opened with authorization URL")
    except:
        print("❌ Could not open browser automatically")
        print(f"   Please manually go to: {auth_url}")
    
    return auth_url

def use_graph_api_explorer():
    """Instructions for using Graph API Explorer (easier method)."""
    
    print("\n" + "="*60)
    print("🛠️ EASIER METHOD: Facebook Graph API Explorer")
    print("="*60)
    
    explorer_url = "https://developers.facebook.com/tools/explorer/"
    
    print(f"🌐 Go to: {explorer_url}")
    print("\n📋 Step-by-step instructions:")
    print("1. Select your app: 'automation_post'")
    print("2. Click 'User Token' → 'Get User Access Token'")
    print("3. Add these permissions:")
    
    permissions = [
        "pages_read_engagement",
        "pages_show_list", 
        "pages_manage_posts",
        "instagram_basic",
        "instagram_content_publish",
        "business_management"
    ]
    
    for i, perm in enumerate(permissions, 1):
        print(f"   {i}. ✅ {perm}")
    
    print("\n4. Click 'Generate Access Token'")
    print("5. Grant all permissions when prompted")
    print("6. Copy the new access token")
    print("7. Update the token in your script")
    
    try:
        webbrowser.open(explorer_url)
        print("\n✅ Opened Graph API Explorer in browser")
    except:
        print(f"\n❌ Please manually go to: {explorer_url}")

def test_new_token():
    """Test a new token input by user."""
    print("\n" + "="*50)
    print("🧪 Test New Access Token")
    print("="*50)
    
    new_token = input("📝 Paste your new access token here: ").strip()
    
    if not new_token:
        print("❌ No token provided")
        return
    
    # Test the new token
    try:
        # Test basic connectivity
        print("🔍 Testing new token...")
        url = "https://graph.facebook.com/v18.0/me"
        params = {"access_token": new_token}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        user_data = response.json()
        
        print(f"✅ Token valid for user: {user_data.get('name')}")
        
        # Test pages access
        url = "https://graph.facebook.com/v18.0/me/accounts"
        params = {
            "access_token": new_token,
            "fields": "name,id,instagram_business_account"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        pages_data = response.json()
        
        pages = pages_data.get('data', [])
        print(f"✅ Found {len(pages)} page(s)")
        
        instagram_found = False
        for page in pages:
            page_name = page.get('name')
            instagram_account = page.get('instagram_business_account')
            
            print(f"   📄 {page_name}")
            if instagram_account:
                instagram_id = instagram_account.get('id')
                print(f"      ✅ Instagram ID: {instagram_id}")
                instagram_found = True
                
                # Save working config
                config = {
                    "access_token": new_token,
                    "instagram_user_id": instagram_id,
                    "page_id": page.get('id'),
                    "page_name": page_name,
                    "app_id": APP_ID,
                    "app_secret": APP_SECRET,
                    "api_version": "v18.0",
                    "status": "ready_for_automation"
                }
                
                with open("instagram_config_fixed.json", "w") as f:
                    json.dump(config, f, indent=2)
                
                print(f"💾 Configuration saved to: instagram_config_fixed.json")
            else:
                print(f"      ❌ No Instagram connected")
        
        if instagram_found:
            print("\n🎉 SUCCESS! Instagram automation is ready!")
        else:
            print("\n⚠️ Token works but no Instagram accounts found")
            print("   Make sure Instagram is connected to your Facebook page")
            
    except Exception as e:
        print(f"❌ Token test failed: {e}")

def main():
    print("=" * 60)
    print("🔧 Instagram Access Token Permission Fixer")
    print("=" * 60)
    
    # Check current permissions
    has_perms, missing = check_current_permissions()
    
    if has_perms:
        print("\n✅ Current token has all required permissions!")
        print("   The issue might be elsewhere. Let's debug further...")
        
        # Test pages access with current token
        try:
            url = "https://graph.facebook.com/v18.0/me/accounts"
            params = {
                "access_token": CURRENT_TOKEN,
                "fields": "name,id,instagram_business_account,access_token"
            }
            
            response = requests.get(url, params=params)
            print(f"\nPages API Response Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
        except Exception as e:
            print(f"Error testing pages: {e}")
    else:
        print(f"\n❌ Missing permissions: {', '.join(missing)}")
        print("   Need to generate new token with correct permissions")
    
    print("\n" + "="*50)
    print("🛠️ SOLUTIONS")
    print("="*50)
    
    print("Choose an option:")
    print("1. Use Graph API Explorer (RECOMMENDED)")
    print("2. Generate OAuth URL")
    print("3. Test new token")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        use_graph_api_explorer()
        input("\nPress Enter after getting new token to test it...")
        test_new_token()
    elif choice == "2":
        generate_auth_url()
    elif choice == "3":
        test_new_token()
    elif choice == "4":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()