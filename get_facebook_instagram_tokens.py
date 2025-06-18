#!/usr/bin/env python3
"""
Easy Facebook & Instagram Token Generator
Step-by-step token generation with copy-paste instructions
"""

def main():
    print("🔐 FACEBOOK & INSTAGRAM TOKEN SETUP")
    print("=" * 60)
    print("Let's get your API tokens step by step!\n")
    
    print("📱 STEP 1: Go to Facebook Developer Console")
    print("https://developers.facebook.com/apps/")
    print("\n🔨 STEP 2: Create App (if you don't have one)")
    print("- Click 'Create App'")
    print("- Choose 'Business'")
    print("- Give it a name like 'Video Poster'")
    print("- Skip Facebook Login for now")
    
    print("\n📋 STEP 3: Add Required Products")
    print("Go to your app dashboard and add these products:")
    print("✓ Instagram Basic Display")
    print("✓ Instagram Graph API")
    print("✓ Facebook Pages API")
    print("✓ Facebook Login")
    
    print("\n🎯 STEP 4: Generate Access Token")
    print("1. Go to Tools > Graph API Explorer")
    print("   https://developers.facebook.com/tools/explorer/")
    print("2. Select your app from dropdown")
    print("3. Click 'Generate Access Token'")
    print("4. Select these permissions:")
    print("   ✓ pages_show_list")
    print("   ✓ pages_manage_posts") 
    print("   ✓ instagram_basic")
    print("   ✓ instagram_content_publish")
    print("   ✓ pages_read_engagement")
    print("5. Click 'Generate Access Token' and authorize")
    
    print("\n⏰ STEP 5: Make Token Long-Lived")
    print("Your token expires in 1 hour. Let's make it last 60 days:")
    print("1. Copy your short-lived token")
    print("2. Go to Access Token Debugger:")
    print("   https://developers.facebook.com/tools/debug/accesstoken/")
    print("3. Paste your token and click 'Debug'")
    print("4. Click 'Extend Access Token'")
    print("5. Copy the new long-lived token")
    
    print("\n📄 STEP 6: Get Your Page Info")
    print("1. Still in Graph API Explorer")
    print("2. Change GET request to: me/accounts")
    print("3. Add fields: name,id,access_token,instagram_business_account")
    print("4. Click Submit")
    print("5. Copy the response - you'll need the IDs")
    
    print("\n🔗 STEP 7: Connect Instagram Business Account")
    print("If you don't see 'instagram_business_account' in the response:")
    print("1. Go to https://business.facebook.com")
    print("2. Select your Facebook Page")
    print("3. Settings > Accounts > Instagram")
    print("4. Connect your Instagram Business account")
    print("5. Repeat Step 6 to get the Instagram Business Account ID")
    
    print("\n💾 STEP 8: Update Your .env File")
    print("Add these lines to your .env file:")
    print("INSTAGRAM_ACCESS_TOKEN=your_long_lived_token")
    print("INSTAGRAM_USER_ID=your_instagram_business_account_id")
    print("FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token")
    print("FACEBOOK_PAGE_ID=your_facebook_page_id")
    
    print("\n🧪 STEP 9: Test Your Setup")
    print("python test_api_tokens.py")
    
    print("\n" + "=" * 60)
    print("🎯 QUICK REFERENCE")
    print("=" * 60)
    print("Facebook Developer Console: https://developers.facebook.com/apps/")
    print("Graph API Explorer: https://developers.facebook.com/tools/explorer/")
    print("Token Debugger: https://developers.facebook.com/tools/debug/accesstoken/")
    print("Business Manager: https://business.facebook.com")
    print("=" * 60)
    
    print("\n💡 TIPS:")
    print("• Make sure your Instagram account is Business/Professional")
    print("• Connect Instagram to Facebook Page BEFORE generating tokens")
    print("• Long-lived tokens last 60 days, then need refresh")
    print("• Save your app ID and app secret somewhere safe")

if __name__ == "__main__":
    main()