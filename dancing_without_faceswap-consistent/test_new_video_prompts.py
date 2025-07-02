#!/usr/bin/env python3
"""
Test the new realistic action prompts for video generation
"""
import random

def load_new_action_prompts():
    """Load the new realistic action prompts"""
    try:
        with open("action_prompts.txt", 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return ["dancing gracefully"]

def generate_sample_video_prompts():
    """Generate sample video prompts using the new action prompts"""
    action_prompts = load_new_action_prompts()
    
    print("🎬 New Realistic Video Prompts")
    print("=" * 60)
    print("Using simple, continuous movements that video AI can actually generate:\n")
    
    # Test different categories
    categories = {
        "Body Movement": [
            "swaying her body side to side",
            "gentle body swaying to music", 
            "rocking her body back and forth",
            "swaying her whole body to music"
        ],
        "Hip Movement": [
            "moving her hips rhythmically",
            "swaying her hips side to side",
            "doing rhythmic hip movements",
            "doing sensual hip sways"
        ],
        "Hand/Arm Dancing": [
            "raising her hands up and down while dancing",
            "moving her arms gracefully while dancing",
            "dancing with expressive hand gestures",
            "moving her hands gracefully up and down"
        ],
        "Walking + Dancing": [
            "walking while dancing seductively",
            "taking small dance steps forward",
            "moving forward with dancing steps"
        ],
        "Combination Movements": [
            "dancing with hand movements and hip sways",
            "moving her body and raising her hands",
            "swaying her hips while moving her arms",
            "moving her torso and arms together"
        ]
    }
    
    for category, prompts in categories.items():
        print(f"📝 {category}:")
        for i, action_prompt in enumerate(prompts, 1):
            video_prompt = f"A beautiful Indian woman {action_prompt}, smooth motion, dynamic movement, cinematic lighting"
            print(f"   {i}. {video_prompt}")
        print()

def compare_old_vs_new():
    """Compare old complex prompts vs new realistic prompts"""
    print("🔄 Comparison: Old vs New Action Prompts")
    print("=" * 60)
    
    comparisons = [
        {
            "old": "spinning around in a circle, skirt flying",
            "new": "swaying her body side to side",
            "reason": "Spinning 360° is too complex → Simple side-to-side sway is achievable"
        },
        {
            "old": "a graceful twirl on one foot", 
            "new": "moving her hips rhythmically",
            "reason": "Twirling requires balance/coordination → Hip movement is natural"
        },
        {
            "old": "a high-energy Bhangra jump",
            "new": "raising her hands up and down while dancing", 
            "reason": "Jumping breaks continuity → Hand movements maintain flow"
        },
        {
            "old": "hands on hips, looking confident",
            "new": "dancing with hand movements and hip sways",
            "reason": "Static pose → Continuous movement"
        },
        {
            "old": "pointing directly at the camera",
            "new": "moving her arms gracefully while dancing",
            "reason": "Single gesture → Flowing arm movements"
        }
    ]
    
    for i, comp in enumerate(comparisons, 1):
        print(f"{i}. ❌ Old: {comp['old']}")
        print(f"   ✅ New: {comp['new']}")
        print(f"   💡 Why: {comp['reason']}\n")

def test_video_prompt_generation():
    """Test video prompt generation with new action prompts"""
    print("🎯 Testing Video Prompt Generation")
    print("=" * 60)
    
    action_prompts = load_new_action_prompts()
    
    print(f"📊 Loaded {len(action_prompts)} new action prompts")
    print(f"🎲 Generating 5 random video prompts:\n")
    
    for i in range(5):
        action_prompt = random.choice(action_prompts)
        video_prompt = f"A beautiful Indian woman {action_prompt}, smooth motion, dynamic movement, cinematic lighting"
        print(f"{i+1}. Action: {action_prompt}")
        print(f"   Video Prompt: {video_prompt}\n")

def analyze_improvements():
    """Analyze the improvements made"""
    print("📈 Analysis of Improvements")
    print("=" * 60)
    
    print("✅ Key Improvements:")
    print("   • Continuous movements instead of single poses")
    print("   • Simple body parts (hips, hands, torso) vs complex choreography")
    print("   • Realistic physics (no spinning, jumping, balancing)")
    print("   • Multiple movement types (body + hands, hips + arms)")
    print("   • Focus on 'dancing' keywords in every prompt")
    
    print(f"\n🎯 Expected Results:")
    print("   • More actual movement in generated videos")
    print("   • Better dancing appearance vs static poses")
    print("   • Smoother, more natural-looking motion")
    print("   • Higher success rate for video generation")
    
    print(f"\n🧪 Testing Recommendations:")
    print("   • Generate videos with new prompts")
    print("   • Compare with previous static results")
    print("   • Check for continuous movement vs poses")
    print("   • Verify dancing appearance vs standing")

def main():
    print("🚀 Testing New Realistic Action Prompts for Dancing Videos")
    print("=" * 80)
    
    generate_sample_video_prompts()
    compare_old_vs_new()
    test_video_prompt_generation()
    analyze_improvements()
    
    print("🎉 Next Steps:")
    print("1. Run automation with new action prompts")
    print("2. Generate videos and compare with previous results")
    print("3. Verify characters are actually dancing vs posing")
    print("4. Fine-tune prompts based on results")

if __name__ == "__main__":
    main()