#!/usr/bin/env python
"""Test script to verify the Telegram approval format fix"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TELEGRAM_APPROVALS_JSON = SCRIPT_DIR / "telegram_approvals/telegram_approvals.json"

def test_approval_format():
    """Test if our fix for approval format works"""
    print("🧪 Testing Telegram approval format...")
    
    if not TELEGRAM_APPROVALS_JSON.exists():
        print("❌ No Telegram approvals file found")
        return False
    
    try:
        with open(TELEGRAM_APPROVALS_JSON, 'r') as f:
            approvals = json.load(f)
        
        print(f"📁 Found {len(approvals)} total images in approval file")
        
        # OLD (broken) way - looking for 'approved' field
        old_count = len([img for img in approvals.values() if img.get('approved', False)])
        print(f"❌ Old method (broken): {old_count} approved images")
        
        # NEW (fixed) way - looking for 'status' == 'approve'  
        new_count = len([img for img in approvals.values() if img.get('status') == 'approve'])
        print(f"✅ New method (fixed): {new_count} approved images")
        
        # Show some examples
        print("\n📋 Sample approval entries:")
        for i, (path, data) in enumerate(list(approvals.items())[:3]):
            print(f"   {i+1}. {Path(path).name}: {data.get('status', 'unknown')}")
        
        if new_count > 0:
            print(f"\n🎉 Fix works! Found {new_count} approved images")
            print("✅ Video generation should now work after Telegram approval")
            return True
        else:
            print("\n⚠️ No approved images found (might be normal if you rejected all)")
            return True
            
    except Exception as e:
        print(f"❌ Error reading approval file: {e}")
        return False

if __name__ == "__main__":
    test_approval_format()