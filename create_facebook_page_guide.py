#!/usr/bin/env python3
"""
Step-by-step guide to create Facebook Page and connect Instagram
"""

def main():
    print("📄 FACEBOOK PAGE CREATION GUIDE")
    print("=" * 60)
    print("You need a Facebook Page to use Instagram Graph API for posting")
    print()
    
    print("🎯 STEP 1: Create Facebook Page")
    print("1. Go to: https://www.facebook.com/pages/create/")
    print("2. Choose 'Business or Brand'")
    print("3. Page Name: Use something like 'Bold Pooja Content' or your brand name")
    print("4. Category: Choose 'Content Creator' or 'Personal Blog'")
    print("5. Add a profile picture (can be same as your Instagram)")
    print("6. Complete the basic setup")
    
    print("\n🔗 STEP 2: Connect Instagram to Facebook Page")
    print("1. Go to: https://business.facebook.com")
    print("2. Select your newly created Facebook Page")
    print("3. Go to Settings > Accounts > Instagram")
    print("4. Click 'Connect Account'")
    print("5. Log in with your Instagram account (@bold.pooja)")
    print("6. Make sure your Instagram is set to Business/Professional account")
    print("   - If not: Instagram app > Settings > Account > Switch to Professional Account")
    
    print("\n🔧 STEP 3: Set Up Facebook App Permissions")
    print("1. Go to: https://developers.facebook.com/apps/")
    print("2. Select your app (or create one if you don't have it)")
    print("3. Go to App Review > Permissions and Features")
    print("4. Request these permissions:")
    print("   • pages_show_list")
    print("   • pages_manage_posts")
    print("   • instagram_basic")
    print("   • instagram_content_publish")
    
    print("\n📱 STEP 4: Verify Instagram Account Type")
    print("In your Instagram app:")
    print("1. Go to Settings > Account")
    print("2. Make sure it says 'Business Account' or 'Creator Account'")
    print("3. If it says 'Personal Account', tap 'Switch to Professional Account'")
    print("4. Choose 'Business' > Select a category > Connect to Facebook Page")
    
    print("\n🧪 STEP 5: Test the Connection")
    print("After completing steps 1-4:")
    print("python get_remaining_ids.py")
    print()
    print("This should now show your Facebook Page and connected Instagram account!")
    
    print("\n" + "=" * 60)
    print("💡 QUICK CHECKLIST")
    print("=" * 60)
    print("□ Facebook Page created")
    print("□ Instagram account is Business/Professional type")
    print("□ Instagram connected to Facebook Page")
    print("□ Facebook app has required permissions")
    print("□ Ran get_remaining_ids.py successfully")
    
    print("\n🎯 ESTIMATED TIME: 10-15 minutes")
    print("📞 If you get stuck, the process is: Page → Connect Instagram → Test")

if __name__ == "__main__":
    main()