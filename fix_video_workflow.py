#!/usr/bin/env python3
"""
Fix Video Workflow - Correct floating point precision issues
"""

import json
from pathlib import Path

def fix_workflow():
    """Fix floating point precision issues in video workflow"""
    print("🔧 FIXING VIDEO WORKFLOW")
    print("=" * 50)
    
    workflow_path = Path("base_workflows/api_wanvideo_without_faceswap.json")
    backup_path = Path("base_workflows/api_wanvideo_without_faceswap.json.backup")
    
    # Create backup
    if not backup_path.exists():
        print("💾 Creating backup...")
        with open(workflow_path, 'r') as f:
            content = f.read()
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"✅ Backup created: {backup_path.name}")
    
    # Load workflow
    with open(workflow_path, 'r') as f:
        workflow = json.load(f)
    
    fixes_applied = []
    
    # Fix WanVideoImageClipEncode node (340)
    if "340" in workflow:
        node = workflow["340"]
        inputs = node.get("inputs", {})
        
        # Fix latent_strength
        if "latent_strength" in inputs:
            old_value = inputs["latent_strength"]
            if old_value != 1.0:
                inputs["latent_strength"] = 1.0
                fixes_applied.append(f"WanVideoImageClipEncode latent_strength: {old_value} → 1.0")
        
        # Fix clip_embed_strength  
        if "clip_embed_strength" in inputs:
            old_value = inputs["clip_embed_strength"]
            if old_value != 1.0:
                inputs["clip_embed_strength"] = 1.0
                fixes_applied.append(f"WanVideoImageClipEncode clip_embed_strength: {old_value} → 1.0")
    
    # Fix WanVideoSampler node (27)
    if "27" in workflow:
        node = workflow["27"]
        inputs = node.get("inputs", {})
        
        # Fix CFG
        if "cfg" in inputs:
            old_value = inputs["cfg"]
            if old_value != 1.0:
                inputs["cfg"] = 1.0
                fixes_applied.append(f"WanVideoSampler cfg: {old_value} → 1.0")
        
        # Fix shift
        if "shift" in inputs:
            old_value = inputs["shift"]
            if old_value != 8.0:
                inputs["shift"] = 8.0
                fixes_applied.append(f"WanVideoSampler shift: {old_value} → 8.0")
    
    # Apply fixes if any were needed
    if fixes_applied:
        print("🔧 Applying fixes:")
        for fix in fixes_applied:
            print(f"  - {fix}")
        
        # Save fixed workflow
        with open(workflow_path, 'w') as f:
            json.dump(workflow, f, indent=2)
        
        print(f"✅ Fixed workflow saved to {workflow_path.name}")
    else:
        print("✅ No fixes needed - workflow already correct")
    
    return len(fixes_applied)

def main():
    """Main function"""
    try:
        fixes_count = fix_workflow()
        
        print("\n🎯 NEXT STEPS TO RESOLVE BLACK VIDEO ISSUE")
        print("=" * 50)
        
        if fixes_count > 0:
            print("✅ Workflow fixes applied.")
        
        print("\n🔍 To diagnose the black video issue further:")
        print("1. Start ComfyUI and check the console for errors")
        print("2. Manually test the video workflow in ComfyUI interface:")
        print("   a. Load: base_workflows/api_wanvideo_without_faceswap.json")
        print("   b. Set LoadImage node to use an approved Shiva image")
        print("   c. Run the workflow and check output")
        print("3. Check if WanVideo models are properly installed:")
        print("   - ComfyUI/models/checkpoints/Wan2_1-I2V-14B-480P_fp8_e5m2.safetensors")
        print("   - ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors")
        print("   - ComfyUI/models/text_encoders/umt5-xxl-enc-bf16.safetensors")
        print("4. Check GPU memory during video generation")
        print("5. Try generating a short test video (reduce num_frames to 25)")
        
        print("\n💡 If videos are still black:")
        print("- The issue is likely in ComfyUI model loading or GPU memory")
        print("- Check ComfyUI console logs during video generation")
        print("- Verify WanVideo extension is properly installed")
        print("- Consider updating ComfyUI and WanVideo to latest versions")
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")

if __name__ == "__main__":
    main()