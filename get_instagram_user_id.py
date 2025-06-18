#!/usr/bin/env python3
"""
Get Instagram User ID using existing access token
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

if not ACCESS_TOKEN:
    print("❌ INSTAGRAM_ACCESS_TOKEN not found in .env file")
    exit(1)

# Get user info
url = f"https://graph.facebook.com/v18.0/me/accounts"
params = {"access_token": ACCESS_TOKEN}

try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    print("📱 Your connected pages/accounts:")
    for account in data.get('data', []):
        print(f"   Name: {account.get('name')}")
        print(f"   ID: {account.get('id')}")
        print(f"   Category: {account.get('category')}")
        print("-" * 40)
    
    # Try to get Instagram business account
    if data.get('data'):
        page_id = data['data'][0]['id']
        page_token = data['data'][0]['access_token']
        
        # Get Instagram business account connected to this page
        insta_url = f"https://graph.facebook.com/v18.0/{page_id}"
        insta_params = {
            "access_token": page_token,
            "fields": "instagram_business_account"
        }
        
        insta_response = requests.get(insta_url, params=insta_params)
        insta_response.raise_for_status()
        insta_data = insta_response.json()
        
        if 'instagram_business_account' in insta_data:
            instagram_id = insta_data['instagram_business_account']['id']
            print(f"✅ Found Instagram Business Account ID: {instagram_id}")
            print(f"\nAdd this to your .env file:")
            print(f"INSTAGRAM_USER_ID={instagram_id}")
        else:
            print("❌ No Instagram Business Account connected to this Facebook Page")
            print("   You need to connect your Instagram account to your Facebook Page")

except requests.exceptions.RequestException as e:
    print(f"❌ Error: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"Response: {e.response.text}")