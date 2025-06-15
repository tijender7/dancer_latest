import os
import json
import requests
from datetime import datetime

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

OLLAMA_MODEL = config["ollama_model"]
NUM_PROMPTS = config["num_prompts"]
COMFYUI_API_URL = config["comfyui_api_url"]
BASE_WORKFLOW_IMAGE = config["base_workflow_image"]
BASE_WORKFLOW_VIDEO = config["base_workflow_video"]
SOURCE_FACES_PATH = config["source_faces_path"]
OUTPUT_FOLDER = config["output_folder"]

# Output timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
os.makedirs("logs", exist_ok=True)

# Example dummy prompt list (replace this with Ollama integration)
prompts = [
    f"Cinematic wide shot of elegant dancer in background {i+1}, soft light, stylized" for i in range(NUM_PROMPTS)
]
with open(f"logs/generated_prompts_{timestamp}.json", "w", encoding="utf-8") as f:
    json.dump({"prompts": prompts}, f, indent=2)

# Load workflows
with open(BASE_WORKFLOW_IMAGE, "r", encoding="utf-8") as f:
    image_workflow = json.load(f)

with open(BASE_WORKFLOW_VIDEO, "r", encoding="utf-8") as f:
    video_workflow = json.load(f)

# Get available face files
face_files = sorted(os.listdir(SOURCE_FACES_PATH))

# 🔹 1. Generate Images First
for i, prompt in enumerate(prompts):
    img_wf = json.loads(json.dumps(image_workflow))  # deep copy
    prompt_node = next(k for k, v in img_wf.items() if v["class_type"] == "Text Multiline")
    face_node = next(k for k, v in img_wf.items() if v["class_type"] == "LoadImage")
    img_wf[prompt_node]["inputs"]["text"] = prompt
    img_wf[face_node]["inputs"]["image"] = face_files[i % len(face_files)]

    print(f"🖼️ Image {i+1} | Face: {face_files[i % len(face_files)]}")
    res = requests.post(COMFYUI_API_URL, json=img_wf)
    if res.ok:
        print(f"✅ Image {i+1} Done")
    else:
        print(f"❌ Image {i+1} Failed: {res.status_code} - {res.text}")

# 🔹 2. Generate Videos Next
for i, prompt in enumerate(prompts):
    vid_wf = json.loads(json.dumps(video_workflow))  # deep copy
    prompt_node = next(k for k, v in vid_wf.items() if v["class_type"] == "Text Multiline")
    face_node = next(k for k, v in vid_wf.items() if v["class_type"] == "LoadImage")
    vid_wf[prompt_node]["inputs"]["text"] = prompt
    vid_wf[face_node]["inputs"]["image"] = face_files[i % len(face_files)]

    print(f"🎬 Video {i+1} | Face: {face_files[i % len(face_files)]}")
    res = requests.post(COMFYUI_API_URL, json=vid_wf)
    if res.ok:
        print(f"✅ Video {i+1} Done")
    else:
        print(f"❌ Video {i+1} Failed: {res.status_code} - {res.text}")
