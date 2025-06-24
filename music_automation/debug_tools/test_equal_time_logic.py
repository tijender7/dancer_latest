#!/usr/bin/env python3
"""
Test the equal time allocation logic without heavy dependencies
"""

def test_equal_time_calculation():
    """Test the time allocation calculation"""
    print("🧪 Testing Equal Time Allocation Logic")
    print("="*50)
    
    # Test scenarios
    scenarios = [
        {"music_duration": 60, "num_videos": 5, "expected_per_video": 12.0},
        {"music_duration": 180, "num_videos": 10, "expected_per_video": 18.0},
        {"music_duration": 90, "num_videos": 3, "expected_per_video": 30.0},
        {"music_duration": 45, "num_videos": 9, "expected_per_video": 5.0},
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        music_duration = scenario["music_duration"]
        num_videos = scenario["num_videos"]
        expected = scenario["expected_per_video"]
        
        calculated = music_duration / num_videos
        
        print(f"\nScenario {i}:")
        print(f"  🎵 Music Duration: {music_duration}s")
        print(f"  📹 Number of Videos: {num_videos}")
        print(f"  ⏱️ Time per Video: {calculated:.1f}s")
        print(f"  ✅ Expected: {expected:.1f}s")
        print(f"  {'✅ PASS' if abs(calculated - expected) < 0.01 else '❌ FAIL'}")
        
        # Show time slots
        print(f"  📊 Time Slots:")
        for j in range(num_videos):
            start_time = j * calculated
            end_time = start_time + calculated
            if j == num_videos - 1:  # Last video gets remaining time
                end_time = music_duration
            print(f"     Video {j+1}: {start_time:.1f}s - {end_time:.1f}s")

def test_forward_backward_pattern():
    """Test the forward-backward pattern logic"""
    print(f"\n🔄 Testing Forward-Backward Pattern Logic")
    print("="*50)
    
    # Test with a scenario: 12 seconds allocated, 2-second segments
    allocated_time = 12.0
    segment_duration = 2.0
    
    print(f"Allocated Time: {allocated_time}s")
    print(f"Segment Duration: {segment_duration}s")
    print(f"Pattern:")
    
    current_time = 0.0
    forward = True
    segment_count = 0
    
    while current_time < allocated_time:
        remaining_time = allocated_time - current_time
        actual_duration = min(segment_duration, remaining_time)
        
        if actual_duration < 0.1:
            break
            
        segment_count += 1
        direction = "Forward" if forward else "Backward"
        end_time = current_time + actual_duration
        
        print(f"  Segment {segment_count}: {current_time:.1f}s-{end_time:.1f}s ({direction})")
        
        current_time += actual_duration
        forward = not forward
    
    print(f"Total Segments: {segment_count}")
    print(f"Total Time Used: {current_time:.1f}s")

if __name__ == "__main__":
    test_equal_time_calculation()
    test_forward_backward_pattern()
    
    print(f"\n🎉 Logic Test Complete!")
    print("="*50)
    print("✅ Ready to run: python music_video_beat_sync_compiler.py")