#!/usr/bin/env python
"""
Test script for deity-focused prompt generation

This script will help test the new deity-focused audio analysis
to ensure prompts are generated consistently for one deity.
"""

import json
from pathlib import Path

def analyze_existing_prompts():
    """Analyze existing prompts to see the current structure"""
    print("🔍 Analyzing existing prompts...")
    
    # Find latest music run folder
    output_base = Path("H:/dancers_content")
    pattern = list(output_base.glob("Run_*_music"))
    
    if not pattern:
        print("❌ No music run folders found")
        return
    
    # Get latest folder
    latest_folder = max(pattern, key=lambda x: x.stat().st_mtime)
    prompts_file = latest_folder / "prompts.json"
    
    if not prompts_file.exists():
        print(f"❌ No prompts.json found in {latest_folder}")
        return
    
    print(f"✅ Found prompts file: {prompts_file}")
    
    # Load and analyze
    with open(prompts_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    segments = data.get('segments', [])
    
    print("\n📊 CURRENT PROMPT ANALYSIS:")
    print("=" * 60)
    print(f"Song: {metadata.get('song_file', 'Unknown')}")
    print(f"Duration: {metadata.get('total_duration', 'Unknown')}s")
    print(f"Total segments: {len(segments)}")
    
    # Check if deity info exists
    if 'primary_deity' in metadata:
        print(f"Primary deity: {metadata['primary_deity']}")
        print(f"Deity attributes: {metadata.get('deity_attributes', [])}")
        print(f"Theme: {metadata.get('consistent_theme', 'Not specified')}")
    else:
        print("❌ No deity information found (old format)")
    
    print("\n📝 SAMPLE PROMPTS:")
    print("-" * 40)
    
    # Show first 3 segments
    for i, segment in enumerate(segments[:3], 1):
        print(f"\nSegment {i} ({segment.get('start_time')}-{segment.get('end_time')}):")
        prompt = segment.get('primary_prompt', 'No prompt')
        print(f"  Prompt: {prompt[:100]}...")
        
        # Check for deity-specific fields
        if 'deity_pose' in segment:
            print(f"  Deity pose: {segment['deity_pose']}")
            print(f"  Deity mood: {segment['deity_mood']}")
            print(f"  Divine setting: {segment['divine_setting']}")
        else:
            print("  ❌ No deity-specific fields (old format)")
    
    # Analyze consistency
    print("\n🎯 CONSISTENCY ANALYSIS:")
    print("-" * 40)
    
    deity_mentions = {}
    for segment in segments:
        prompt = segment.get('primary_prompt', '').lower()
        
        # Count deity mentions
        deities = ['shiva', 'ganesha', 'krishna', 'hanuman', 'durga', 'rama', 'vishnu', 'lakshmi']
        for deity in deities:
            if deity in prompt:
                deity_mentions[deity] = deity_mentions.get(deity, 0) + 1
    
    if deity_mentions:
        print("Deity mentions across segments:")
        for deity, count in deity_mentions.items():
            percentage = (count / len(segments)) * 100
            print(f"  {deity.title()}: {count}/{len(segments)} ({percentage:.1f}%)")
        
        # Check consistency
        max_deity = max(deity_mentions.items(), key=lambda x: x[1])
        if max_deity[1] >= len(segments) * 0.8:
            print(f"✅ Good consistency: {max_deity[0].title()} appears in {max_deity[1]}/{len(segments)} segments")
        else:
            print(f"⚠️ Low consistency: Most frequent deity ({max_deity[0].title()}) only in {max_deity[1]}/{len(segments)} segments")
    else:
        print("❌ No deity mentions found in prompts")

def show_deity_examples():
    """Show examples of what deity-focused prompts should look like"""
    print("\n\n🎨 DEITY-FOCUSED PROMPT EXAMPLES:")
    print("=" * 60)
    
    examples = {
        "Lord Shiva": [
            "Photorealistic image of Lord Shiva in deep meditation pose with blue skin, crescent moon on forehead, Ganges flowing from hair, sitting in lotus position on Mount Kailash with cosmic energy surrounding him, serene expression, 16:9 aspect ratio, divine glow lighting, medium shot, centered composition",
            "Photorealistic image of Lord Shiva as Nataraja in cosmic dance pose with four arms, one leg raised, surrounded by ring of fire, blue skin glowing, hair flowing with cosmic energy, tiger skin dhoti, dynamic powerful expression, 16:9 aspect ratio, dramatic lighting, wide shot, dynamic composition",
            "Photorealistic image of Lord Shiva in blessing pose with third eye glowing, holding trident, snake around neck, sitting on tiger skin in ancient temple, compassionate expression, devotees in background, 16:9 aspect ratio, cinematic lighting, rule of thirds composition"
        ],
        "Lord Ganesha": [
            "Photorealistic image of Lord Ganesha sitting on lotus throne with elephant head, large belly, four arms holding modak and blessing mudra, golden yellow dhoti, mouse vahana at feet, wise benevolent expression, temple setting with flowers, 16:9 aspect ratio, soft divine lighting, medium shot, centered composition",
            "Photorealistic image of Lord Ganesha in dancing pose with elephant head tilted joyfully, all four arms in graceful mudras, colorful silk dhoti, anklets with bells, flower garlands, festival celebration background, joyful expression, 16:9 aspect ratio, vibrant lighting, dynamic angle, diagonal composition",
            "Photorealistic image of Lord Ganesha removing obstacles with powerful gesture, elephant head with determined expression, holding broken tusk as pen, surrounded by golden light, devotees praying in background, protective mood, 16:9 aspect ratio, dramatic lighting, close-up shot, rule of thirds composition"
        ]
    }
    
    for deity, prompts in examples.items():
        print(f"\n{deity.upper()}:")
        print("-" * 30)
        for i, prompt in enumerate(prompts, 1):
            print(f"{i}. {prompt}")
    
    print("\n🔑 KEY CONSISTENCY ELEMENTS:")
    print("-" * 30)
    print("✅ Same deity name in EVERY prompt")
    print("✅ Consistent physical attributes (skin color, clothing, accessories)")
    print("✅ Deity-specific symbols and items")
    print("✅ Appropriate settings for the deity")
    print("✅ Varying poses and moods while maintaining identity")
    print("✅ Technical specs consistent across all prompts")

def generate_sample_deity_json():
    """Generate a sample JSON showing the new deity-focused structure"""
    sample_data = {
        "metadata": {
            "song_file": "shiva_bhajan.mp3",
            "total_duration": 60.0,
            "total_segments": 12,
            "primary_deity": "Lord Shiva",
            "deity_attributes": [
                "cosmic dancer",
                "meditation master", 
                "destroyer of evil",
                "lord of transformation",
                "blue-skinned divine being"
            ],
            "consistent_theme": "All prompts focus on Lord Shiva with variations in pose, mood, and divine setting",
            "generation_timestamp": "2025-06-19T19:45:00.000000",
            "processing_stats": {
                "total_api_calls": 1,
                "retry_count": 0,
                "total_processing_time": "45.2s",
                "success_rate": "100%"
            }
        },
        "segments": [
            {
                "segment_id": 1,
                "start_time": "00:00",
                "end_time": "00:05",
                "primary_prompt": "Photorealistic image of Lord Shiva in deep meditation pose with blue skin, crescent moon on forehead, Ganges flowing from hair, third eye closed in concentration, sitting in lotus position on Mount Kailash with snow-capped peaks in background, serene peaceful expression, 16:9 aspect ratio, soft divine glow lighting, medium shot, centered composition",
                "deity_pose": "meditation",
                "deity_mood": "serene",
                "divine_setting": "Mount Kailash",
                "style_tags": ["photorealistic", "divine", "cinematic", "devotional"],
                "energy_level": "low",
                "technical_specs": {
                    "aspect_ratio": "16:9",
                    "lighting": "divine glow",
                    "camera_angle": "medium shot",
                    "composition": "centered"
                }
            },
            {
                "segment_id": 2,
                "start_time": "00:05",
                "end_time": "00:10",
                "primary_prompt": "Photorealistic image of Lord Shiva as Nataraja in cosmic dance pose with four arms, one leg raised in divine dance, surrounded by ring of fire, blue skin radiating power, hair flowing with cosmic energy, tiger skin dhoti, damaru drum in hand, fierce yet graceful expression, 16:9 aspect ratio, dramatic fiery lighting, wide shot, dynamic composition",
                "deity_pose": "cosmic dance",
                "deity_mood": "powerful",
                "divine_setting": "cosmic space",
                "style_tags": ["photorealistic", "divine", "cinematic", "dynamic"],
                "energy_level": "high",
                "technical_specs": {
                    "aspect_ratio": "16:9",
                    "lighting": "dramatic",
                    "camera_angle": "wide shot",
                    "composition": "dynamic"
                }
            }
        ]
    }
    
    output_file = Path("sample_deity_focused_prompts.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Sample deity-focused JSON saved to: {output_file}")
    print("\nThis shows the NEW structure with:")
    print("✅ Primary deity identification")
    print("✅ Deity attributes list")
    print("✅ Consistent theme description")
    print("✅ Deity-specific fields per segment (pose, mood, setting)")
    print("✅ Focused prompts featuring same deity throughout")

if __name__ == "__main__":
    print("🎭 DEITY-FOCUSED PROMPT ANALYSIS & TESTING")
    print("=" * 60)
    
    # Analyze existing prompts
    analyze_existing_prompts()
    
    # Show examples
    show_deity_examples()
    
    # Generate sample
    generate_sample_deity_json()
    
    print("\n\n🚀 NEXT STEPS:")
    print("-" * 20)
    print("1. Run: python audio_to_prompts_generator.py")
    print("2. Check the new prompts.json for deity consistency")
    print("3. Run: python music_pipeline_all_in_one.py")
    print("4. Verify generated images feature same deity throughout")
    print("\n✨ The new approach will create cohesive devotional videos!")