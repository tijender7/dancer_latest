#!/usr/bin/env python3
"""
Diagnose Black Video Issue - Analyze the video workflow configuration
"""

import json
from pathlib import Path
import os

def analyze_workflow():
    """Analyze the video workflow for potential issues"""
    print("🔍 ANALYZING VIDEO WORKFLOW FOR BLACK VIDEO ISSUE")
    print("=" * 60)
    
    # Load workflow
    workflow_path = Path("base_workflows/api_wanvideo_without_faceswap.json")
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    print(f"📄 Workflow: {workflow_path.name}")
    print(f"📊 Total nodes: {len(workflow)}")
    
    # Find key nodes
    load_image_node = None
    wanvideo_encode_node = None
    wanvideo_sampler_node = None
    wanvideo_decode_node = None
    
    for node_id, node_data in workflow.items():
        class_type = node_data.get("class_type")
        if class_type == "LoadImage":
            load_image_node = (node_id, node_data)
        elif class_type == "WanVideoImageClipEncode":
            wanvideo_encode_node = (node_id, node_data)
        elif class_type == "WanVideoSampler":
            wanvideo_sampler_node = (node_id, node_data)
        elif class_type == "WanVideoDecode":
            wanvideo_decode_node = (node_id, node_data)
    
    # Analyze LoadImage node
    if load_image_node:
        node_id, node_data = load_image_node
        print(f"\n📸 LoadImage Node ({node_id}):")
        print(f"  - Current image path: '{node_data['inputs']['image']}'")
        print(f"  - Title: {node_data.get('_meta', {}).get('title', 'No title')}")
        print("  ✅ LoadImage node found")
    else:
        print("\n❌ LoadImage node not found!")
    
    # Analyze WanVideoImageClipEncode node
    if wanvideo_encode_node:
        node_id, node_data = wanvideo_encode_node
        inputs = node_data['inputs']
        print(f"\n🎬 WanVideoImageClipEncode Node ({node_id}):")
        print(f"  - Generation width: {inputs.get('generation_width', 'Not set')}")
        print(f"  - Generation height: {inputs.get('generation_height', 'Not set')}")
        print(f"  - Number of frames: {inputs.get('num_frames', 'Not set')}")
        print(f"  - Noise aug strength: {inputs.get('noise_aug_strength', 'Not set')}")
        print(f"  - Latent strength: {inputs.get('latent_strength', 'Not set')}")
        print(f"  - Clip embed strength: {inputs.get('clip_embed_strength', 'Not set')}")
        print(f"  - Adjust resolution: {inputs.get('adjust_resolution', 'Not set')}")
        print(f"  - Force offload: {inputs.get('force_offload', 'Not set')}")
        
        # Check image input connection
        image_input = inputs.get('image', [])
        if isinstance(image_input, list) and len(image_input) >= 2:
            source_node, output_index = image_input[0], image_input[1]
            if load_image_node and str(source_node) == load_image_node[0]:
                print(f"  ✅ Connected to LoadImage node {source_node}[{output_index}]")
            else:
                print(f"  ❌ Connected to wrong node: {source_node}[{output_index}]")
        else:
            print(f"  ❌ Invalid image input: {image_input}")
    else:
        print("\n❌ WanVideoImageClipEncode node not found!")
    
    # Analyze WanVideoSampler node
    if wanvideo_sampler_node:
        node_id, node_data = wanvideo_sampler_node
        inputs = node_data['inputs']
        print(f"\n⚙️ WanVideoSampler Node ({node_id}):")
        print(f"  - Steps: {inputs.get('steps', 'Not set')}")
        print(f"  - CFG: {inputs.get('cfg', 'Not set')}")
        print(f"  - Shift: {inputs.get('shift', 'Not set')}")
        print(f"  - Denoise strength: {inputs.get('denoise_strength', 'Not set')}")
        print(f"  - Scheduler: {inputs.get('scheduler', 'Not set')}")
        
        # Check critical connections
        image_embeds = inputs.get('image_embeds', [])
        if isinstance(image_embeds, list) and len(image_embeds) >= 2:
            source_node = image_embeds[0]
            if wanvideo_encode_node and str(source_node) == wanvideo_encode_node[0]:
                print(f"  ✅ Image embeds connected to WanVideoImageClipEncode")
            else:
                print(f"  ❌ Image embeds connected to wrong node: {source_node}")
        else:
            print(f"  ❌ Invalid image_embeds input: {image_embeds}")
    else:
        print("\n❌ WanVideoSampler node not found!")
    
    # Check for potential issues
    print(f"\n🚨 POTENTIAL ISSUES:")
    issues_found = []
    
    if wanvideo_encode_node:
        _, node_data = wanvideo_encode_node
        inputs = node_data['inputs']
        
        # Check noise augmentation strength
        noise_aug = inputs.get('noise_aug_strength', 0)
        if noise_aug > 0.1:
            issues_found.append(f"High noise_aug_strength ({noise_aug}) might cause black videos")
        
        # Check latent strength
        latent_strength = inputs.get('latent_strength', 1.0)
        if latent_strength != 1.0:
            issues_found.append(f"Non-standard latent_strength ({latent_strength})")
        
        # Check resolution
        width = inputs.get('generation_width', 0)
        height = inputs.get('generation_height', 0)
        if width != 832 or height != 480:
            issues_found.append(f"Non-standard resolution ({width}x{height})")
    
    if wanvideo_sampler_node:
        _, node_data = wanvideo_sampler_node
        inputs = node_data['inputs']
        
        # Check denoise strength
        denoise = inputs.get('denoise_strength', 1.0)
        if denoise != 1.0:
            issues_found.append(f"Non-standard denoise_strength ({denoise})")
        
        # Check CFG
        cfg = inputs.get('cfg', 1.0)
        if cfg < 1.0 or cfg > 10.0:
            issues_found.append(f"Unusual CFG value ({cfg})")
    
    if issues_found:
        for i, issue in enumerate(issues_found, 1):
            print(f"  {i}. {issue}")
    else:
        print("  ✅ No obvious configuration issues found")
    
    return issues_found

def analyze_test_image():
    """Analyze the test image used"""
    print(f"\n📸 ANALYZING TEST IMAGE")
    print("=" * 60)
    
    image_path = Path("H:/dancers_content/250621/250621163629_00019_.png")
    
    if not image_path.exists():
        print(f"❌ Test image not found: {image_path}")
        return
    
    try:
        # Get basic file info without PIL
        stat = image_path.stat()
        print(f"📄 Image: {image_path.name}")
        print(f"📊 File size: {stat.st_size} bytes")
        
        if stat.st_size == 0:
            print("❌ Image file is empty!")
        elif stat.st_size < 1000:
            print("⚠️ Image file seems very small")
        else:
            print("✅ Image file size looks reasonable")
            
        print("✅ Basic image analysis complete")
            
    except Exception as e:
        print(f"❌ Failed to analyze image: {e}")

def main():
    """Main diagnostic function"""
    try:
        workflow_issues = analyze_workflow()
        analyze_test_image()
        
        print(f"\n🎯 SUMMARY & RECOMMENDATIONS")
        print("=" * 60)
        
        if workflow_issues:
            print("🔧 Try these fixes:")
            for i, issue in enumerate(workflow_issues, 1):
                if "noise_aug_strength" in issue:
                    print(f"  {i}. Reduce noise_aug_strength to 0.02 or lower")
                elif "latent_strength" in issue:
                    print(f"  {i}. Set latent_strength to 1.0")
                elif "denoise_strength" in issue:
                    print(f"  {i}. Set denoise_strength to 1.0") 
                elif "resolution" in issue:
                    print(f"  {i}. Use standard 832x480 resolution")
                elif "CFG" in issue:
                    print(f"  {i}. Set CFG between 1.0-7.0")
        else:
            print("🎯 The workflow configuration looks correct.")
            print("   The black video issue might be caused by:")
            print("   1. ComfyUI model loading issues")
            print("   2. GPU memory problems") 
            print("   3. Image preprocessing in ComfyUI")
            print("   4. WanVideo model compatibility")
        
        print(f"\n💡 Next steps:")
        print("   1. Check ComfyUI console for errors during video generation")
        print("   2. Verify all WanVideo models are loaded correctly")
        print("   3. Test with a simpler image (smaller, different format)")
        print("   4. Check ComfyUI memory usage during video generation")
            
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")

if __name__ == "__main__":
    main()