#!/usr/bin/env python3
"""
YouTube Metadata Generator for Dancer Content Pipeline
Generates viral titles/descriptions/tags based on theme and attire data from automation runs.
"""

import os
import sys
import json
import time
import re
import random
from pathlib import Path
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# === CONFIGURATION ===
BASE_DIR = Path(__file__).resolve().parent
DANCERS_CONTENT_BASE = Path(r"H:\dancers_content")  # Same as your upload script
CONTENT_PLAN_OUTPUT = "content_plan.json"  # Output for YouTube uploader

# Ollama Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 120))
MAX_RETRIES = 3

# YouTube Optimization Settings
TITLE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 5000
TAGS_MAX_COUNT = 20

class ThemeAttireMetadataGenerator:
    def __init__(self):
        self.viral_keywords = {
            "dance_styles": ["bhangra", "bollywood", "garba", "thumri", "fusion", "classical"],
            "viral_triggers": ["viral", "trending", "hot", "amazing", "incredible", "stunning", "gorgeous"],
            "engagement_hooks": ["can't believe", "wait for it", "watch till end", "mind blown", "jaw dropping"],
            "location_descriptors": ["luxury", "exclusive", "rooftop", "beachside", "royal", "modern", "traditional"],
            "attire_descriptors": ["revealing", "traditional", "fusion", "glamorous", "ethnic", "contemporary"]
        }

    def find_latest_run_data(self) -> Optional[Dict]:
        """Find the most recent run with complete theme/attire data."""
        try:
            run_folders = sorted(
                [d for d in DANCERS_CONTENT_BASE.iterdir() if d.is_dir() and d.name.startswith("Run_")],
                key=lambda x: x.stat().st_mtime, reverse=True
            )
            
            for run_folder in run_folders:
                # Look for the detailed JSON with theme/attire data
                details_files = list(run_folder.glob("*_details_theme_attire_v6.json"))
                if details_files:
                    with open(details_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Validate we have theme and attire data
                    metadata = data.get("run_metadata", {})
                    if metadata.get("run_theme") and metadata.get("run_attire"):
                        print(f"✅ Found run data: {run_folder.name}")
                        print(f"    Theme: {metadata['run_theme'][:60]}...")
                        print(f"    Attire: {metadata['run_attire'][:60]}...")
                        return data
                        
            print("⚠️ No recent runs with theme/attire data found")
            return None
            
        except Exception as e:
            print(f"ERROR: Failed to find run data: {e}")
            return None

    def extract_theme_keywords(self, theme: str) -> List[str]:
        """Extract key descriptive words from theme description."""
        theme_lower = theme.lower()
        keywords = []
        
        # Location-based keywords
        if "mumbai" in theme_lower: keywords.extend(["mumbai", "bollywood"])
        if "goa" in theme_lower: keywords.extend(["goa", "beach", "resort"])
        if "punjabi" in theme_lower: keywords.extend(["punjabi", "bhangra"])
        if "rajasthan" in theme_lower: keywords.extend(["rajasthan", "royal", "palace"])
        if "kerala" in theme_lower: keywords.extend(["kerala", "beach"])
        
        # Venue-based keywords
        if "police" in theme_lower: keywords.extend(["police", "uniform", "officer"])
        if "hospital" in theme_lower: keywords.extend(["nurse", "medical", "hospital"])
        if "office" in theme_lower: keywords.extend(["office", "corporate", "secretary"])
        if "college" in theme_lower: keywords.extend(["college", "student", "campus"])
        if "gym" in theme_lower: keywords.extend(["gym", "fitness", "workout"])
        if "restaurant" in theme_lower: keywords.extend(["chef", "kitchen", "restaurant"])
        
        # Event-based keywords
        if "wedding" in theme_lower: keywords.extend(["wedding", "celebration", "traditional"])
        if "festival" in theme_lower: keywords.extend(["festival", "celebration", "cultural"])
        if "party" in theme_lower: keywords.extend(["party", "celebration", "dance"])
        
        return list(set(keywords))

    def extract_attire_keywords(self, attire: str) -> List[str]:
        """Extract key descriptive words from attire description."""
        attire_lower = attire.lower()
        keywords = []
        
        # Traditional clothing
        if any(word in attire_lower for word in ["saree", "choli", "lehenga"]):
            keywords.extend(["traditional", "indian", "ethnic"])
        if "ghagra" in attire_lower: keywords.extend(["ghagra", "traditional"])
        if "sharara" in attire_lower: keywords.extend(["sharara", "ethnic"])
        
        # Style descriptors
        if any(word in attire_lower for word in ["revealing", "tiny", "barely", "micro"]):
            keywords.extend(["bold", "confident", "stunning"])
        if any(word in attire_lower for word in ["sequined", "embroidery", "mirror-work"]):
            keywords.extend(["glamorous", "decorated", "ornate"])
        
        # Professional uniforms
        if "uniform" in attire_lower: keywords.extend(["uniform", "professional"])
        if any(word in attire_lower for word in ["nurse", "medical"]):
            keywords.extend(["nurse", "medical", "healthcare"])
        if "office" in attire_lower: keywords.extend(["office", "professional", "business"])
        
        return list(set(keywords))

    def call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Make API call to Ollama with retries."""
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                print(f"INFO: Ollama API call (Attempt {attempt+1}/{MAX_RETRIES+1})...")
                r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
                r.raise_for_status()
                resp_json = r.json()
                
                response_text = resp_json.get("response", "")
                
                # Find JSON in the response
                json_match = re.search(r'(\{.*?\})', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                
                # Try parsing entire response as JSON
                return json.loads(response_text)
                
            except Exception as e:
                print(f"WARN: Ollama call failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(2)
                    
        print("FATAL: Ollama failed after all retries")
        return self.generate_fallback_metadata()

    def generate_fallback_metadata(self) -> Dict[str, Any]:
        """Generate basic metadata as fallback."""
        return {
            "title": "Stunning Indian Dance Performance 💃",
            "description": "Watch this incredible dance performance! Like and subscribe for more amazing content! 🔥\n\n#IndianDance #Viral #Trending",
            "tags": ["indian dance", "bollywood", "viral", "trending", "dance", "performance", "amazing", "stunning"]
        }

    def generate_viral_metadata(self, theme: str, attire: str, run_metadata: Dict) -> Dict[str, Any]:
        """Generate viral YouTube metadata based on theme and attire."""
        
        # Extract keywords
        theme_keywords = self.extract_theme_keywords(theme)
        attire_keywords = self.extract_attire_keywords(attire)
        
        # Create optimized prompt for viral content
        prompt = f"""You are a viral YouTube content strategist specializing in Indian dance content. 
Create EXTREMELY viral and engaging metadata for a YouTube Short based on this content:

THEME/LOCATION: {theme}
OUTFIT/ATTIRE: {attire}
KEY THEME WORDS: {', '.join(theme_keywords)}
KEY ATTIRE WORDS: {', '.join(attire_keywords)}

Requirements:
- Title: Maximum {TITLE_MAX_LENGTH} characters, include emojis, use viral keywords like "You Won't Believe", "Wait For It", "Mind Blown"
- Description: 2-3 paragraphs, emotionally engaging, include call-to-action, use relevant hashtags
- Tags: {TAGS_MAX_COUNT} highly searchable tags mixing dance keywords, theme keywords, and viral terms

Focus on:
- Indian dance performance content
- Professional/themed scenarios (if applicable)
- Cultural celebration and beauty
- Viral engagement triggers
- YouTube Shorts optimization

Respond ONLY with valid JSON:
{{"title": "...", "description": "...", "tags": ["tag1", "tag2", ...]}}"""

        return self.call_ollama(prompt)

    def create_multiple_variations(self, theme: str, attire: str, run_metadata: Dict, count: int = 5) -> List[Dict]:
        """Generate multiple viral metadata variations."""
        variations = []
        
        for i in range(count):
            print(f"INFO: Generating variation {i+1}/{count}...")
            metadata = self.generate_viral_metadata(theme, attire, run_metadata)
            
            # Add variation identifier
            metadata["variation_id"] = i + 1
            metadata["generation_timestamp"] = datetime.now().isoformat()
            metadata["source_theme"] = theme[:100] + "..." if len(theme) > 100 else theme
            metadata["source_attire"] = attire[:100] + "..." if len(attire) > 100 else attire
            
            variations.append(metadata)
            
            # Small delay between generations for variety
            if i < count - 1:
                time.sleep(1)
                
        return variations

    def save_content_plan(self, variations: List[Dict], run_data: Dict) -> None:
        """Save content plan in format expected by YouTube uploader."""
        
        # Transform variations into the format expected by your uploader
        content_blocks = []
        for var in variations:
            content_blocks.append({
                "title_template": var["title"],
                "description_template": var["description"], 
                "tags": var["tags"],
                "metadata": {
                    "variation_id": var["variation_id"],
                    "source_theme": var["source_theme"],
                    "source_attire": var["source_attire"],
                    "generation_timestamp": var["generation_timestamp"]
                }
            })
        
        # Create final content plan
        content_plan = {
            "generated_timestamp": datetime.now().isoformat(),
            "source_run": run_data.get("run_metadata", {}).get("timestamp", "unknown"),
            "run_theme": run_data.get("run_metadata", {}).get("run_theme", "unknown"),
            "run_attire": run_data.get("run_metadata", {}).get("run_attire", "unknown"),
            "total_variations": len(variations),
            "content_blocks": content_blocks
        }
        
        # Save to file
        output_path = BASE_DIR / CONTENT_PLAN_OUTPUT
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(content_plan, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Content plan saved: {output_path}")
        print(f"    Generated {len(content_blocks)} viral variations")
        
        # Also save detailed variations for reference
        detailed_path = BASE_DIR / f"detailed_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(detailed_path, 'w', encoding='utf-8') as f:
            json.dump({
                "content_plan": content_plan,
                "detailed_variations": variations,
                "source_run_data": run_data
            }, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Detailed metadata saved: {detailed_path}")

def main():
    print("=" * 80)
    print("🎬 VIRAL YOUTUBE METADATA GENERATOR FOR DANCER CONTENT")
    print("=" * 80)
    
    generator = ThemeAttireMetadataGenerator()
    
    # Step 1: Find latest run data
    print("[1] Finding latest run with theme/attire data...")
    run_data = generator.find_latest_run_data()
    if not run_data:
        print("FATAL: No suitable run data found")
        sys.exit(1)
    
    # Step 2: Extract theme and attire
    metadata = run_data["run_metadata"]
    theme = metadata["run_theme"]
    attire = metadata["run_attire"]
    
    print(f"\n[2] Extracted content details:")
    print(f"    📍 Theme: {theme}")
    print(f"    👗 Attire: {attire}")
    print(f"    📊 Run Stats: {metadata.get('images_submitted', 0)} images, {metadata.get('videos_submitted', 0)} videos")
    
    # Step 3: Generate multiple viral variations
    print(f"\n[3] Generating viral metadata variations...")
    variations = generator.create_multiple_variations(theme, attire, metadata, count=8)
    
    # Step 4: Save content plan
    print(f"\n[4] Saving content plan...")
    generator.save_content_plan(variations, run_data)
    
    # Step 5: Show preview
    print(f"\n[5] Preview of generated content:")
    print("-" * 60)
    for i, var in enumerate(variations[:3], 1):  # Show first 3
        print(f"Variation {i}:")
        print(f"  📝 Title: {var['title']}")
        print(f"  📋 Tags: {', '.join(var['tags'][:5])}...")
        print()
    
    print("=" * 80)
    print("✅ METADATA GENERATION COMPLETE!")
    print(f"   Content plan ready for YouTube uploader: {CONTENT_PLAN_OUTPUT}")
    print("=" * 80)

if __name__ == "__main__":
    main()