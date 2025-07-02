#!/usr/bin/env python3
"""
Analyze video prompt differences between original and current automation
"""

def current_automation_video_prompt():
    """Current automation video prompt format"""
    action_prompts = [
        "waving to the camera with a big smile",
        "hands on hips, looking confident", 
        "spinning around in a circle, skirt flying",
        "doing a classic Bollywood dance pose",
        "doing a gentle hip sway from side to side",
        "a graceful twirl on one foot",
        "a high-energy Bhangra jump",
        "doing a seductive body roll"
    ]
    
    print("🎬 Current Automation Video Prompts:")
    print("=" * 50)
    
    for i, action_prompt in enumerate(action_prompts[:5], 1):
        video_prompt = f"A beautiful Indian woman {action_prompt}, smooth motion, dynamic movement, cinematic lighting"
        print(f"{i}. {video_prompt}")
    
    return action_prompts

def enhanced_video_prompts():
    """Enhanced video prompts for better dancing"""
    action_prompts = [
        "waving to the camera with a big smile",
        "hands on hips, looking confident", 
        "spinning around in a circle, skirt flying",
        "doing a classic Bollywood dance pose",
        "doing a gentle hip sway from side to side",
        "a graceful twirl on one foot",
        "a high-energy Bhangra jump",
        "doing a seductive body roll"
    ]
    
    print(f"\n🎭 Enhanced Video Prompts for Better Dancing:")
    print("=" * 50)
    
    # Option 1: More dancing keywords
    print("Option 1: More dancing keywords")
    for i, action_prompt in enumerate(action_prompts[:3], 1):
        video_prompt = f"A beautiful Indian woman {action_prompt}, fluid motion, graceful dancing, rhythmic movement, cinematic lighting, professional video quality"
        print(f"{i}. {video_prompt}")
    
    print(f"\nOption 2: Simplified focus on movement")
    for i, action_prompt in enumerate(action_prompts[3:6], 1):
        video_prompt = f"Beautiful Indian woman {action_prompt}, smooth motion, dynamic movement"
        print(f"{i}. {video_prompt}")
    
    print(f"\nOption 3: Dance-specific terms")
    for i, action_prompt in enumerate(action_prompts[6:8], 1):
        video_prompt = f"A beautiful Indian woman {action_prompt}, fluid dance motion, rhythmic movement, graceful choreography, high quality video"
        print(f"{i}. {video_prompt}")

def analyze_video_prompt_structure():
    """Analyze what makes good video prompts"""
    print(f"\n📊 Video Prompt Analysis:")
    print("=" * 50)
    
    print("✅ Good video prompt elements:")
    print("   • Action-focused (not appearance-focused)")
    print("   • Movement keywords: 'smooth motion', 'dynamic movement'")
    print("   • Dancing terms: 'graceful', 'rhythmic', 'fluid'")
    print("   • Simple structure (not overly complex)")
    print("   • Quality terms: 'cinematic lighting', 'high quality'")
    
    print(f"\n❌ Bad video prompt elements:")
    print("   • Too much character description")
    print("   • Static pose descriptions")
    print("   • Excessive appearance details")
    print("   • Complex background descriptions")
    print("   • Overly long prompts")
    
    print(f"\n🎯 Recommended video prompt template:")
    print("   'A beautiful Indian woman {action_prompt}, smooth motion, dynamic movement, cinematic lighting'")
    
    print(f"\n🔍 Potential improvements:")
    print("   1. Add more dancing-specific keywords")
    print("   2. Ensure action prompts are truly dynamic")
    print("   3. Test different movement keywords")
    print("   4. Consider video-specific quality terms")

def recommend_improvements():
    """Recommend specific improvements for dancing videos"""
    print(f"\n💡 Recommendations for Better Dancing Videos:")
    print("=" * 60)
    
    print("1. 📝 Enhanced Action Prompts:")
    enhanced_actions = [
        "performing a graceful Bollywood dance sequence",
        "doing energetic Bhangra dance moves", 
        "performing a sensual Indian classical dance",
        "dancing with flowing hand gestures",
        "doing a rhythmic hip sway dance",
        "performing a twirling dance move",
        "executing a dynamic dance turn",
        "dancing with expressive arm movements"
    ]
    
    for action in enhanced_actions[:4]:
        print(f"   • {action}")
    
    print(f"\n2. 🎬 Video Prompt Keywords:")
    print("   Current: 'smooth motion, dynamic movement, cinematic lighting'")
    print("   Enhanced: 'fluid dance motion, rhythmic movement, graceful choreography, cinematic lighting'")
    
    print(f"\n3. 🧪 Testing Approach:")
    print("   • Test with more dance-specific action prompts")
    print("   • Try different movement keywords")
    print("   • Compare video quality with original automation")
    print("   • A/B test different prompt structures")
    
    print(f"\n4. ⚙️ Implementation:")
    print("   • Update action_prompts.txt with more dance-focused actions")
    print("   • Modify video prompt template to emphasize dancing")
    print("   • Test and compare results")

def main():
    print("🚀 Video Prompt Analysis for Better Dancing Videos")
    print("=" * 60)
    
    current_automation_video_prompt()
    enhanced_video_prompts()
    analyze_video_prompt_structure()
    recommend_improvements()
    
    print(f"\n🎉 Next Steps:")
    print("1. Update action prompts to be more dance-focused")
    print("2. Enhance video prompt template with better dancing keywords")
    print("3. Test the improved prompts")
    print("4. Compare with original automation results")

if __name__ == "__main__":
    main()