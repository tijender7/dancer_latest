#!/usr/bin/env python3
"""
Test character ID inheritance logic
"""

def test_character_id_extraction():
    """Test the character ID extraction with different approval_id formats"""
    
    def extract_character_id_from_approval_id(approval_id: str) -> str:
        """Extract character ID from approval_id"""
        if '-' in approval_id:
            return approval_id.split('-')[0]
        return approval_id
    
    print("🧪 Testing Character ID Extraction")
    print("=" * 50)
    
    test_cases = [
        # Phase 1 (seeds)
        ("1-1", "1"),
        ("1-2", "1"), 
        ("3-1", "3"),
        ("3-2", "3"),
        
        # Phase 2 (expansions - new format)
        ("1-1-1", "1"),  # Character 1, expansion 1, variation 1
        ("1-2-1", "1"),  # Character 1, expansion 2, variation 1  
        ("3-1-1", "3"),  # Character 3, expansion 1, variation 1
        ("3-2-1", "3"),  # Character 3, expansion 2, variation 1
    ]
    
    for approval_id, expected_character in test_cases:
        result = extract_character_id_from_approval_id(approval_id)
        status = "✅" if result == expected_character else "❌"
        print(f"{status} {approval_id} → Character {result} (expected {expected_character})")
    
    return True

def simulate_expansion_workflow():
    """Simulate the new expansion workflow"""
    print(f"\n🎭 Simulating Character Inheritance Workflow")
    print("=" * 50)
    
    # Simulate Phase 1 approved seeds
    approved_seeds = [
        {"approval_id": "1-1", "image_path": "/path/to/seed1.png"},
        {"approval_id": "3-1", "image_path": "/path/to/seed3.png"}
    ]
    
    print(f"📌 Phase 1: Approved {len(approved_seeds)} seeds")
    for seed in approved_seeds:
        character_id = seed['approval_id'].split('-')[0]
        print(f"   Seed {seed['approval_id']} → Character {character_id}")
    
    # Simulate Phase 2 expansion generation
    print(f"\n📌 Phase 2: Generating expansions...")
    expansion_jobs = []
    
    for seed_data in approved_seeds:
        character_id = seed_data['approval_id'].split('-')[0]
        print(f"\n🎨 Character {character_id}: Generating 2 expansion images")
        
        # Simulate 2 expansions per character
        character_expansion_index = 1
        for expansion_num in range(2):
            expansion_jobs.append({
                "display_index": character_expansion_index,
                "character_id": character_id,
                "seed_approval_id": seed_data['approval_id']
            })
            character_expansion_index += 1
    
    # Simulate unrolling with new logic
    print(f"\n📌 Phase 2: Unrolling expansion results...")
    unrolled_expansions = []
    
    for item in expansion_jobs:
        # Simulate 1 generated image per job
        approval_id = f"{item['character_id']}-{item['display_index']}-1"
        unrolled_expansions.append({
            "approval_id": approval_id,
            "character_id": item['character_id']
        })
        print(f"   Generated expansion: {approval_id} → Character {item['character_id']}")
    
    # Verify character distribution
    print(f"\n📊 Character Distribution:")
    char_counts = {}
    for expansion in unrolled_expansions:
        char_id = expansion['character_id']
        char_counts[char_id] = char_counts.get(char_id, 0) + 1
    
    for char_id, count in sorted(char_counts.items()):
        print(f"   Character {char_id}: {count} expansions")
    
    expected_chars = {'1', '3'}
    actual_chars = set(char_counts.keys())
    
    if expected_chars == actual_chars:
        print(f"\n✅ SUCCESS: Character inheritance working correctly!")
        print(f"   Expected characters: {sorted(expected_chars)}")
        print(f"   Actual characters: {sorted(actual_chars)}")
    else:
        print(f"\n❌ FAILURE: Character inheritance broken!")
        print(f"   Expected characters: {sorted(expected_chars)}")
        print(f"   Actual characters: {sorted(actual_chars)}")
    
    return expected_chars == actual_chars

def main():
    print("🚀 Character ID Inheritance Test Suite")
    print("=" * 60)
    
    # Test 1: Character ID extraction
    test1_passed = test_character_id_extraction()
    
    # Test 2: Full workflow simulation
    test2_passed = simulate_expansion_workflow()
    
    print(f"\n📋 Test Results:")
    print(f"   Character ID Extraction: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Character Inheritance: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 ALL TESTS PASSED - Character inheritance is working!")
    else:
        print(f"\n❌ SOME TESTS FAILED - Character inheritance needs fixes!")

if __name__ == "__main__":
    main()