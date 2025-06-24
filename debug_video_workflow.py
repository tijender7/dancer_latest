#!/usr/bin/env python3
"""
Debug Video Workflow - Check if image path is correctly injected
"""

import json
import copy
from pathlib import Path

# Load the video workflow
workflow_path = Path("base_workflows/api_wanvideo_without_faceswap.json")
with open(workflow_path, 'r') as f:
    workflow = json.load(f)

print("=== VIDEO WORKFLOW DEBUG ===")
print(f"Total nodes: {len(workflow)}")

# Find the LoadImage node
load_image_node = None
load_image_id = None
for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "LoadImage":
        load_image_node = node_data
        load_image_id = node_id
        break

if load_image_node:
    print(f"\n🔍 Found LoadImage node: {load_image_id}")
    print(f"📄 Node details:")
    print(f"  - Class: {load_image_node['class_type']}")
    print(f"  - Title: {load_image_node.get('_meta', {}).get('title', 'No title')}")
    print(f"  - Current image path: '{load_image_node['inputs']['image']}'")
    
    # Test image injection
    test_image_path = "temp_video_starts/test_image.png"
    print(f"\n🧪 Testing image injection...")
    print(f"Before: {load_image_node['inputs']['image']}")
    
    # Simulate the API server injection
    test_workflow = copy.deepcopy(workflow)
    test_workflow[load_image_id]["inputs"]["image"] = test_image_path
    
    print(f"After:  {test_workflow[load_image_id]['inputs']['image']}")
    
    # Check if injection worked
    if test_workflow[load_image_id]["inputs"]["image"] == test_image_path:
        print("✅ Image injection works correctly")
    else:
        print("❌ Image injection failed")
        
else:
    print("❌ No LoadImage node found in workflow")

# Check WanVideoImageClipEncode node which uses the LoadImage
print(f"\n🔍 Checking WanVideoImageClipEncode node...")
for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "WanVideoImageClipEncode":
        print(f"Found WanVideoImageClipEncode: {node_id}")
        image_input = node_data.get("inputs", {}).get("image", [])
        print(f"  - Image input: {image_input}")
        if isinstance(image_input, list) and len(image_input) == 2:
            source_node_id = image_input[0]
            if str(source_node_id) == str(load_image_id):
                print("✅ WanVideoImageClipEncode correctly connected to LoadImage")
            else:
                print(f"❌ WanVideoImageClipEncode connected to wrong node: {source_node_id}")
        break

print("\n=== END DEBUG ===")