import os
import sys
import json
import time
import re
from pathlib import Path
import requests
from datetime import datetime

# === CONFIGURATION ===
BASE_DIR = Path(__file__).resolve().parent
PROJECT_PREFIX = "MultiTweetReport"
NARRATION_FILENAME = "combined_script_english.json"
OUTPUT_FILENAME = "youtube_video_metadata.json"

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 120))
MAX_RETRIES = 2

def find_latest_project_folder(base_dir: Path, prefix="MultiTweetReport"):
    candidates = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith(prefix)]
    if not candidates:
        print(f"[FATAL] No {prefix}_* project folders found.")
        sys.exit(1)
    latest = max(candidates, key=lambda d: d.stat().st_mtime)
    print(f"[INFO] Using project folder: {latest}")
    return latest

def load_narration_text(project_folder: Path, filename: str):
    narration_path = project_folder / filename
    if not narration_path.is_file():
        print(f"[FATAL] Narration file not found: {narration_path}")
        sys.exit(1)
    with open(narration_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Try common keys, fallback to full string if needed
    for key in ("final_video_script", "script_text"):
        if key in data and isinstance(data[key], str):
            return data[key]
    # Fallback: try reading the whole file as a string
    return json.dumps(data)

def call_ollama(prompt, model=OLLAMA_MODEL, url=OLLAMA_URL, timeout=OLLAMA_TIMEOUT):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    for attempt in range(MAX_RETRIES + 1):
        try:
            print(f"[INFO] Ollama API call (Attempt {attempt+1}/{MAX_RETRIES+1})...")
            r = requests.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            resp_json = r.json()
            # Some Ollama builds use .get("response"), others .get("message") or full .text
            text = resp_json.get("response") or resp_json.get("message") or r.text
            # Find the first {...} JSON object in the response
            match = re.search(r'(\{.*?\})', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            # Fallback: try loading full string as JSON
            return json.loads(text)
        except Exception as e:
            print(f"[WARN] Ollama call failed: {e}")
            time.sleep(2)
    print("[FATAL] Ollama failed to return valid JSON after retries.")
    sys.exit(1)

def main():
    # 1. Find latest project folder
    project_folder = find_latest_project_folder(BASE_DIR, PROJECT_PREFIX)
    # 2. Load narration text
    narration = load_narration_text(project_folder, NARRATION_FILENAME)

    # 3. Generate metadata using Ollama
    prompt = (
        "You are an AI assistant for YouTube creators. Based on the video script below, "
        "generate a catchy YouTube video title, an emotionally engaging and curiosity-driven 2-3 paragraph description, "
        "and a list of 10-20 relevant tags. Respond ONLY with valid JSON in this format:\n"
        "{\"title\": \"...\", \"description\": \"...\", \"tags\": [\"tag1\", \"tag2\"]}\n"
        f"Video Script:\n{narration}\n"
    )
    metadata = call_ollama(prompt)

    # 4. Save output to youtube_video_metadata.json in project folder
    out_path = project_folder / OUTPUT_FILENAME
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[✅] Metadata saved to: {out_path.resolve()}")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
