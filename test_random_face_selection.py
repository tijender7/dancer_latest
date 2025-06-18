#!/usr/bin/env python3
"""
Test script to verify random face selection functionality
"""
import sys
import json
from pathlib import Path

# Add the current directory to the path to import our modified API server
sys.path.insert(0, str(Path(__file__).parent))

# Import the function from our modified API server
from api_server_v5_withfaceswap import get_random_face_from_source, SOURCE_FACES_PATH_CONFIG

def test_random_face_selection():
    """Test the random face selection function"""
    print("Testing Random Face Selection")
    print("=" * 40)
    
    print(f"Source faces directory: {SOURCE_FACES_PATH_CONFIG}")
    print(f"Directory exists: {SOURCE_FACES_PATH_CONFIG.is_dir()}")
    
    if SOURCE_FACES_PATH_CONFIG.is_dir():
        # List all files in the directory
        all_files = list(SOURCE_FACES_PATH_CONFIG.iterdir())
        print(f"All files in directory: {len(all_files)}")
        for f in all_files:
            print(f"  - {f.name}")
        print()
    
    # Test multiple random selections
    print("Testing random face selection (10 iterations):")
    selections = []
    for i in range(10):
        selected = get_random_face_from_source()
        selections.append(selected)
        print(f"  {i+1}: {selected}")
    
    # Show unique selections
    unique_selections = set(filter(None, selections))
    print(f"\nUnique faces selected: {len(unique_selections)}")
    for face in sorted(unique_selections):
        print(f"  - {face}")
    
    print(f"\nTotal successful selections: {len([s for s in selections if s is not None])}")
    print(f"Failed selections: {len([s for s in selections if s is None])}")

if __name__ == "__main__":
    test_random_face_selection()