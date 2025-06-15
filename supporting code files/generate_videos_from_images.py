import os
import sys
import time
from gradio_client import Client, handle_file

# ====== USER CONFIGURATION ======
GRADIO_API_URL = "[http://127.0.0.1](http://127.0.0.1):42003/"
PROMPT = "jumping dancing shaking breast"
N_PROMPT = ""
SEED = 31337
VIDEO_LENGTH = 15
LATENT_WINDOW_SIZE = 9
STEPS = 25
CFG = 1
GS = 10
RS = 0
GPU_MEMORY_PRESERVATION = 6
USE_TEACACHE = True

IMAGES_FOLDER = r"H:\dancers_content\Run_20250424_115712\all_images\250424"
OUTPUT_FOLDER = r"H:\dancers_content\Run_20250424_115712\videos"

# ====== END USER CONFIGURATION ======

def ensure_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"[INFO] Created output folder: {folder_path}")

def get_image_files(folder):
    valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
    all_files = os.listdir(folder)
    image_files = [f for f in all_files if f.lower().endswith(valid_exts) and os.path.isfile(os.path.join(folder, f))]
    return image_files

def main():
    print(f"[INFO] Checking input folder: {IMAGES_FOLDER}")
    if not os.path.isdir(IMAGES_FOLDER):
        print(f"[ERROR] IMAGES_FOLDER does not exist: {IMAGES_FOLDER}")
        sys.exit(1)
    ensure_folder(OUTPUT_FOLDER)

    # Debug: Show all files found in the directory
    all_files = os.listdir(IMAGES_FOLDER)
    print(f"[DEBUG] Files in IMAGES_FOLDER ({len(all_files)}): {all_files}")

    image_files = get_image_files(IMAGES_FOLDER)
    print(f"[DEBUG] Image files detected ({len(image_files)}): {image_files}")

    if not image_files:
        print(f"[WARNING] No image files found in {IMAGES_FOLDER}")
        sys.exit(0)

    client = Client(GRADIO_API_URL)
    print(f"[INFO] Found {len(image_files)} images. Starting video generation...")

    for idx, filename in enumerate(image_files, 1):
        img_path = os.path.join(IMAGES_FOLDER, filename)
        print(f"[{idx}/{len(image_files)}] Processing {img_path} ...")
        try:
            result = client.predict(
                input_image=handle_file(img_path),
                prompt=PROMPT,
                n_prompt=N_PROMPT,
                seed=SEED,
                total_second_length=VIDEO_LENGTH,
                latent_window_size=LATENT_WINDOW_SIZE,
                steps=STEPS,
                cfg=CFG,
                gs=GS,
                rs=RS,
                gpu_memory_preservation=GPU_MEMORY_PRESERVATION,
                use_teacache=USE_TEACACHE,
                api_name="/process"
            )
            # result[0] is a dict with 'video' key
            video_path = result[0]['video']
            if not os.path.isfile(video_path):
                print(f"[ERROR] Video file not found at {video_path}")
                continue
            out_video_path = os.path.join(
                OUTPUT_FOLDER, f"{os.path.splitext(filename)[0]}_video.mp4"
            )
            os.replace(video_path, out_video_path)
            print(f"[SUCCESS] Saved video to {out_video_path}")
        except Exception as e:
            print(f"[ERROR] Failed for {img_path}: {e}")
        # Optional: sleep to avoid overloading the API
        time.sleep(1)

    print("[INFO] Video generation complete.")

if __name__ == "__main__":
    main()