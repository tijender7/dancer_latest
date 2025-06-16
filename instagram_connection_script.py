#!/usr/bin/env python3
"""
Instagram Business Account Auto-Connector
Programmatically connects Instagram to Facebook Page and finds User ID
"""

import requests
import json
import time
import webbrowser
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment variables
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
APP_ID = os.getenv("INSTAGRAM_APP_ID")
PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")  
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

# Validate required environment variables
required_vars = {
    "INSTAGRAM_ACCESS_TOKEN": ACCESS_TOKEN,
    "INSTAGRAM_APP_ID": APP_ID,
    "INSTAGRAM_PAGE_ID": PAGE_ID,
    "INSTAGRAM_USERNAME": INSTAGRAM_USERNAME
}

missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]
if missing_vars:
    print("ERROR: Missing required environment variables:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease add these to your .env file")
    exit(1)

class InstagramBusinessConnector:
    """Automated Instagram Business account connector."""
    
    def __init__(self):
        self.access_token = ACCESS_TOKEN
        self.app_id = APP_ID
        self.page_id = PAGE_ID
        self.instagram_username = INSTAGRAM_USERNAME
        
    def get_page_access_token(self) -> str:
        """Get page-specific access token."""
        print("🔑 Getting page access token...")
        
        url = f"https://graph.facebook.com/v18.0/me/accounts"
        params = {
            "access_token": self.access_token,
            "fields": "name,id,access_token"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for page in data.get('data', []):
                if page.get('id') == self.page_id:
                    page_token = page.get('access_token')
                    if page_token:
                        print(f"✅ Page access token obtained")
                        return page_token
            
            print(f"❌ Could not get page access token for page {self.page_id}")
            return None
            
        except Exception as e:
            print(f"❌ Error getting page token: {e}")
            return None
    
    def connect_instagram_to_page_programmatically(self, page_token: str) -> str:
        """Try to connect Instagram account to page via API."""
        print("🔗 Attempting programmatic Instagram connection...")
        
        # Method 1: Try to connect via Pages API
        url = f"https://graph.facebook.com/v18.0/{self.page_id}/instagram_accounts"
        
        # First, try to get available Instagram accounts
        params = {"access_token": page_token}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            accounts = data.get('data', [])
            print(f"📱 Found {len(accounts)} Instagram account(s) available for connection")
            
            for account in accounts:
                username = account.get('username', 'Unknown')
                account_id = account.get('id')
                print(f"   • @{username} (ID: {account_id})")
                
                if username.lower() == self.instagram_username.lower():
                    print(f"✅ Found matching Instagram account: @{username}")
                    return account_id
            
            # If no direct match, try alternative methods
            return self.try_alternative_connection_methods(page_token)
            
        except Exception as e:
            print(f"⚠️ Direct connection failed: {e}")
            return self.try_alternative_connection_methods(page_token)
    
    def try_alternative_connection_methods(self, page_token: str) -> str:
        """Try alternative methods to find Instagram connection."""
        print("\n🔄 Trying alternative connection methods...")
        
        # Method 1: Search via Instagram Basic Display
        print("🔍 Method 1: Searching via Instagram Basic Display...")
        instagram_id = self.search_via_instagram_basic_display()
        if instagram_id:
            return instagram_id
        
        # Method 2: Use Business Discovery API
        print("🔍 Method 2: Using Business Discovery API...")
        instagram_id = self.search_via_business_discovery()
        if instagram_id:
            return instagram_id
        
        # Method 3: Manual OAuth flow for Instagram
        print("🔍 Method 3: Manual Instagram OAuth...")
        return self.manual_instagram_oauth()
    
    def search_via_instagram_basic_display(self) -> str:
        """Search using Instagram Basic Display API."""
        try:
            # Try to get Instagram accounts from user
            url = f"https://graph.facebook.com/v18.0/me"
            params = {
                "access_token": self.access_token,
                "fields": "accounts{instagram_business_account{id,username}}"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            print(f"   Raw response: {json.dumps(data, indent=2)}")
            
            # Parse response for Instagram accounts
            accounts = data.get('accounts', {}).get('data', [])
            for account in accounts:
                instagram_account = account.get('instagram_business_account')
                if instagram_account:
                    username = instagram_account.get('username', '')
                    if username.lower() == self.instagram_username.lower():
                        instagram_id = instagram_account.get('id')
                        print(f"✅ Found via Basic Display: @{username} (ID: {instagram_id})")
                        return instagram_id
            
            return None
            
        except Exception as e:
            print(f"   ❌ Basic Display search failed: {e}")
            return None
    
    def search_via_business_discovery(self) -> str:
        """Search using Business Discovery API."""
        try:
            # Use Instagram Business Discovery to find account
            url = f"https://graph.facebook.com/v18.0/{self.page_id}"
            params = {
                "access_token": self.access_token,
                "fields": f"instagram_business_account,business_discovery.username({self.instagram_username}){{id,username,account_type}}"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            print(f"   Business Discovery response: {json.dumps(data, indent=2)}")
            
            # Check for instagram_business_account
            instagram_account = data.get('instagram_business_account')
            if instagram_account:
                instagram_id = instagram_account.get('id')
                print(f"✅ Found via Business Discovery: ID {instagram_id}")
                return instagram_id
            
            # Check business_discovery result
            business_discovery = data.get('business_discovery')
            if business_discovery:
                username = business_discovery.get('username', '')
                account_type = business_discovery.get('account_type', '')
                if username.lower() == self.instagram_username.lower() and account_type == 'BUSINESS':
                    instagram_id = business_discovery.get('id')
                    print(f"✅ Found via Business Discovery: @{username} (ID: {instagram_id})")
                    return instagram_id
            
            return None
            
        except Exception as e:
            print(f"   ❌ Business Discovery search failed: {e}")
            return None
    
    def manual_instagram_oauth(self) -> str:
        """Guide through manual Instagram OAuth flow."""
        print("\n🔗 MANUAL INSTAGRAM CONNECTION REQUIRED")
        print("=" * 50)
        
        # Generate Instagram OAuth URL
        redirect_uri = "https://localhost/"
        instagram_oauth_url = (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={self.app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=user_profile,user_media"
            f"&response_type=code"
        )
        
        print("📋 Steps to connect Instagram:")
        print("1. We'll open Instagram OAuth in your browser")
        print("2. Login and authorize the app")
        print("3. Copy the code from the redirect URL")
        print("4. We'll exchange it for Instagram User ID")
        
        proceed = input("\nProceed with manual OAuth? (y/n): ").lower()
        
        if proceed == 'y':
            try:
                webbrowser.open(instagram_oauth_url)
                print("✅ Browser opened with Instagram OAuth")
                print(f"🌐 URL: {instagram_oauth_url}")
                
                # Wait for user to complete OAuth
                auth_code = input("\nPaste the 'code' parameter from redirect URL: ").strip()
                
                if auth_code:
                    return self.exchange_instagram_code_for_id(auth_code)
                else:
                    print("❌ No authorization code provided")
                    return None
                    
            except Exception as e:
                print(f"❌ OAuth process failed: {e}")
                return None
        
        return None
    
    def exchange_instagram_code_for_id(self, auth_code: str) -> str:
        """Exchange Instagram OAuth code for User ID."""
        print("🔄 Exchanging authorization code for Instagram User ID...")
        
        # This would require Instagram Basic Display API setup
        # For now, we'll use a different approach
        print("⚠️ Instagram OAuth exchange requires additional setup")
        print("💡 Let's try to connect manually and then search again...")
        
        return self.retry_connection_after_manual_setup()
    
    def retry_connection_after_manual_setup(self) -> str:
        """Retry finding Instagram connection after manual setup."""
        print("\n🔄 RETRY AFTER MANUAL CONNECTION")
        print("=" * 40)
        print("Please complete these steps manually:")
        print("1. Open Instagram app on your phone")
        print("2. Profile → Menu → Settings → Account → Linked Accounts")
        print("3. Tap Facebook → Select 'Dance Content Creator AI'")
        print("4. Grant all permissions")
        print()
        print("OR via Facebook:")
        print(f"1. Go to facebook.com/{PAGE_ID}")
        print("2. Settings → Instagram → Connect Account")
        print("3. Login with @hot_reels_x0x0")
        
        input("\nPress Enter after completing manual connection...")
        
        # Retry searching for the connection
        print("🔍 Searching for Instagram connection again...")
        
        # Try all methods again
        for attempt in range(3):
            print(f"\n🔄 Attempt {attempt + 1}/3")
            
            # Method 1: Direct page search
            instagram_id = self.search_connected_instagram()
            if instagram_id:
                return instagram_id
            
            # Wait between attempts
            if attempt < 2:
                print("⏳ Waiting 10 seconds before retry...")
                time.sleep(10)
        
        print("❌ Still unable to find Instagram connection via API")
        return self.create_manual_config()
    
    def search_connected_instagram(self) -> str:
        """Search for connected Instagram account."""
        try:
            url = f"https://graph.facebook.com/v18.0/me/accounts"
            params = {
                "access_token": self.access_token,
                "fields": "name,id,instagram_business_account{id,username,account_type}"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for page in data.get('data', []):
                page_name = page.get('name', '')
                instagram_account = page.get('instagram_business_account')
                
                if instagram_account:
                    username = instagram_account.get('username', '')
                    account_type = instagram_account.get('account_type', '')
                    instagram_id = instagram_account.get('id')
                    
                    print(f"   📄 {page_name}")
                    print(f"      📱 @{username} ({account_type}) - ID: {instagram_id}")
                    
                    if username.lower() == self.instagram_username.lower():
                        print(f"✅ FOUND MATCH: @{username}")
                        return instagram_id
            
            return None
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return None
    
    def create_manual_config(self) -> str:
        """Create config file manually with known information."""
        print("\n💡 CREATING MANUAL CONFIGURATION")
        print("=" * 40)
        
        print("Since API detection isn't working, let's create config manually:")
        
        # Ask user for Instagram User ID
        instagram_id = input(f"Enter Instagram User ID for @{self.instagram_username} (if known): ").strip()
        
        if not instagram_id:
            print("💡 You can find Instagram User ID by:")
            print("1. Go to: https://developers.facebook.com/tools/explorer/")
            print("2. Use your access token")
            print(f"3. Query: {self.page_id}?fields=instagram_business_account")
            print("4. Look for the 'id' field in instagram_business_account")
            
            instagram_id = input("Instagram User ID: ").strip()
        
        if instagram_id:
            # Create working config
            config = {
                "instagram_user_id": instagram_id,
                "page_id": self.page_id,
                "page_name": "Dance Content Creator AI",
                "instagram_username": self.instagram_username,
                "access_token": self.access_token,
                "app_id": self.app_id,
                "api_version": "v18.0",
                "connection_method": "manual_configuration",
                "created_timestamp": datetime.now().isoformat(),
                "status": "ready_for_testing"
            }
            
            with open("instagram_config_manual.json", "w") as f:
                json.dump(config, f, indent=2)
            
            print(f"💾 Manual configuration saved: instagram_config_manual.json")
            return instagram_id
        
        return None
    
    def test_instagram_connection(self, instagram_id: str) -> bool:
        """Test if Instagram User ID works."""
        print(f"\n🧪 Testing Instagram connection with ID: {instagram_id}")
        
        url = f"https://graph.facebook.com/v18.0/{instagram_id}"
        params = {
            "access_token": self.access_token,
            "fields": "account_type,username,name,media_count,followers_count"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            username = data.get('username', 'Unknown')
            account_type = data.get('account_type', 'Unknown')
            media_count = data.get('media_count', 'Unknown')
            followers_count = data.get('followers_count', 'Unknown')
            
            print(f"✅ Instagram account test successful!")
            print(f"   📱 @{username}")
            print(f"   🏢 Type: {account_type}")
            print(f"   📸 Posts: {media_count}")
            print(f"   👥 Followers: {followers_count}")
            
            if account_type == 'BUSINESS':
                print(f"🎉 Perfect! Account is Business type - ready for automation!")
                return True
            else:
                print(f"⚠️ Account type should be BUSINESS for posting API")
                return False
                
        except Exception as e:
            print(f"❌ Instagram test failed: {e}")
            return False

def main():
    print("=" * 60)
    print("🔗 INSTAGRAM BUSINESS ACCOUNT AUTO-CONNECTOR")
    print("   Programmatic Instagram + Facebook connection")
    print("=" * 60)
    
    connector = InstagramBusinessConnector()
    
    # Step 1: Get page access token
    page_token = connector.get_page_access_token()
    if not page_token:
        print("❌ Could not get page access token")
        return
    
    # Step 2: Try to connect Instagram programmatically
    instagram_id = connector.connect_instagram_to_page_programmatically(page_token)
    
    # Step 3: Test the connection
    if instagram_id:
        if connector.test_instagram_connection(instagram_id):
            print(f"\n🎉 SUCCESS! Instagram automation ready!")
            print(f"📱 Instagram User ID: {instagram_id}")
            print(f"✅ Ready to run automated posting!")
            
            # Save final working config
            final_config = {
                "instagram_user_id": instagram_id,
                "page_id": connector.page_id,
                "access_token": connector.access_token,
                "app_id": connector.app_id,
                "setup_completed": True,
                "ready_for_automation": True
            }
            
            with open("instagram_config_final.json", "w") as f:
                json.dump(final_config, f, indent=2)
            
            print(f"💾 Final config saved: instagram_config_final.json")
        else:
            print(f"\n⚠️ Connection found but test failed")
    else:
        print(f"\n❌ Could not establish Instagram connection")
        print(f"💡 You may need to connect manually via Instagram app")

if __name__ == "__main__":
    main()