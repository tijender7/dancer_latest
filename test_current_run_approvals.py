#!/usr/bin/env python
"""Test script to verify current run approval filtering works"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TELEGRAM_APPROVALS_JSON = SCRIPT_DIR / "telegram_approvals/telegram_approvals.json"

def test_current_run_filtering():
    """Test if our current run filtering works"""
    print("🧪 Testing current run approval filtering...")
    
    if not TELEGRAM_APPROVALS_JSON.exists():
        print("❌ No Telegram approvals file found")
        return False
    
    try:
        with open(TELEGRAM_APPROVALS_JSON, 'r') as f:
            approvals = json.load(f)
        
        print(f"📁 Found {len(approvals)} total images in approval file")
        
        # Simulate current run images (from your recent run)
        current_run_images = [
            "H:\\dancers_content\\250620\\250620093014_00213_.png",
            "H:\\dancers_content\\250620\\250620093014_00214_.png", 
            "H:\\dancers_content\\250620\\250620093014_00215_.png",
            "H:\\dancers_content\\250620\\250620093014_00216_.png",
            "H:\\dancers_content\\250620\\250620093014_00217_.png",
            "H:\\dancers_content\\250620\\250620093014_00218_.png",
            "H:\\dancers_content\\250620\\250620093014_00219_.png",
            "H:\\dancers_content\\250620\\250620093014_00220_.png"
        ]
        
        current_image_paths = set(current_run_images)
        print(f"🎯 Current run has {len(current_image_paths)} images")
        
        # Filter approvals to only include current run images
        current_run_approvals = {}
        for img_path, approval_data in approvals.items():
            if img_path in current_image_paths:
                current_run_approvals[img_path] = approval_data
        
        total_current_images = len(current_run_approvals)
        approved_count = len([img for img in current_run_approvals.values() if img.get('status') == 'approve'])
        rejected_count = len([img for img in current_run_approvals.values() if img.get('status') == 'reject'])
        pending_count = total_current_images - approved_count - rejected_count
        
        print(f"\n📊 Current run approval status:")
        print(f"   Total current run images: {total_current_images}")
        print(f"   ✅ Approved: {approved_count}")
        print(f"   ❌ Rejected: {rejected_count}")
        print(f"   ⏳ Pending: {pending_count}")
        
        print(f"\n📋 Current run approval details:")
        for img_path, approval_data in current_run_approvals.items():
            img_name = Path(img_path).name
            status = approval_data.get('status', 'unknown')
            print(f"   {img_name}: {status}")
        
        if total_current_images > 0 and (approved_count + rejected_count) == total_current_images:
            print(f"\n🎉 All current run images reviewed!")
            print(f"✅ Video generation should start with {approved_count} approved images")
            return True
        else:
            print(f"\n⏳ Still waiting for {pending_count} images to be reviewed")
            return False
            
    except Exception as e:
        print(f"❌ Error reading approval file: {e}")
        return False

if __name__ == "__main__":
    test_current_run_filtering()