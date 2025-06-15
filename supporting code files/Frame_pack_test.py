import os
import shutil
import time
import sys
from gradio_client import Client, handle_file
from gradio_client.utils import Status # Import Status enum

# --- Configuration ---
API_URL = "http://127.0.0.1:7860/"
INPUT_IMAGE_PATH = r"H:\dancers_content\Run_20250425_090553\all_images\250425\250425090554_001_swapped_00002_.png"
PROMPT = "dancing with clear moves"
NEGATIVE_PROMPT = "low quality, blurry, deformed, text, watermark"

# --- Parameters matching the /process API ---
SEED = -1
TOTAL_SECOND_LENGTH = 5.0
LATENT_WINDOW_SIZE = 9.0
STEPS = 25.0
CFG = 1.0
GS = 10.0
RS = 0.0
GPU_MEMORY_PRESERVATION = 6.0
USE_TEACACHE = True

# --- Helper Function ---
def get_safe_filename(filepath):
    base = os.path.basename(filepath)
    name, ext = os.path.splitext(base)
    safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).rstrip()
    return safe_name if safe_name else "generated_video"

# --- Main Logic ---
if not os.path.exists(INPUT_IMAGE_PATH):
    print(f"Error: Input image not found at {INPUT_IMAGE_PATH}")
    exit()

output_dir = os.path.dirname(INPUT_IMAGE_PATH)
base_filename = get_safe_filename(INPUT_IMAGE_PATH)
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_filename = f"{base_filename}_generated_{timestamp}.mp4"
destination_path = os.path.join(output_dir, output_filename)

print(f"Connecting to API at {API_URL}...")
job = None
try:
    client = Client(API_URL, verbose=False)

    print(f"Sending image: {INPUT_IMAGE_PATH}")
    print(f"Prompt: {PROMPT}")
    print(f"Duration: {TOTAL_SECOND_LENGTH} seconds")
    print("Submitting video generation job...")

    job = client.submit(
        input_image=handle_file(INPUT_IMAGE_PATH),
        prompt=PROMPT,
        n_prompt=NEGATIVE_PROMPT,
        seed=float(SEED) if SEED != -1 else 31337.0,
        total_second_length=float(TOTAL_SECOND_LENGTH),
        latent_window_size=float(LATENT_WINDOW_SIZE),
        steps=float(STEPS),
        cfg=float(CFG),
        gs=float(GS),
        rs=float(RS),
        gpu_memory_preservation=float(GPU_MEMORY_PRESERVATION),
        use_teacache=bool(USE_TEACACHE),
        api_name="/process"
    )

    print("Job submitted. Waiting for completion...")

    last_status_code = None
    while True:
        try:
            status = job.status()
            # Use status.code instead of status.name
            current_status_code = status.code

            if current_status_code != last_status_code:
                 # status.code is an Enum (like Status.PROCESSING), print its name
                print(f"\rCurrent Status: {current_status_code.name} ({status.eta:.1f}s eta)" if status.eta else f"\rCurrent Status: {current_status_code.name}", end="")
                sys.stdout.flush()
                last_status_code = current_status_code

            if current_status_code == Status.FINISHED:
                print("\nJob finished!")
                break
            elif current_status_code == Status.ERRORED:
                # Use status.code.name for printing the error status
                print(f"\nJob failed! Check server logs (Pinokio terminal). Status: {current_status_code.name}")
                try:
                    print(f"Attempting to get final result/error: {job.result()}")
                except Exception as inner_e:
                    print(f"Could not retrieve final result/error details: {inner_e}")
                exit()

            time.sleep(0.5)

        except AttributeError:
             # Handle cases where status object might be malformed or missing code
             print("\rStatus object malformed, waiting...", end="")
             sys.stdout.flush()
             time.sleep(1)
        except Exception as status_e:
            print(f"\nError checking job status: {status_e}")
            print("Attempting to get final result anyway...")
            break

    print("Retrieving final result...")
    result = job.result()

    # --- Process the final result (same as before) ---
    if isinstance(result, (tuple, list)) and len(result) > 0 and isinstance(result[0], dict):
        video_info = result[0]
        if 'video' in video_info and video_info['video'] is not None:
            temp_video_path = video_info['video']
            if isinstance(temp_video_path, str) and os.path.exists(temp_video_path):
                print(f"Video generated successfully at temporary path: {temp_video_path}")
                print(f"Moving video to: {destination_path}")
                os.makedirs(output_dir, exist_ok=True)
                shutil.move(temp_video_path, destination_path)
                print(f"Video saved successfully to: {destination_path}")
            else:
                 print(f"Error: API returned video info, but the path is invalid or file doesn't exist.")
                 print(f"Received video info: {video_info}")
        else:
            print("Error: Job finished, but the 'video' key is missing or None in the result.")
            print("****** CHECK THE PINOKIO/SERVER TERMINAL FOR ERRORS ******")
            print(f"Received first element of result: {result[0]}")
            print(f"Full result tuple: {result}")

    else:
        print("Error: Job finished, but API did not return the expected tuple structure.")
        print("****** CHECK THE PINOKIO/SERVER TERMINAL FOR ERRORS ******")
        print(f"Received result type: {type(result)}")
        print(f"Received result: {result}")


except Exception as e:
    print(f"\nAn error occurred: {e}")
    if job:
        try:
            # Try printing status even if main loop failed
            print(f"Final job status before error: {job.status()}")
        except Exception as final_status_e:
             print(f"Could not get final status: {final_status_e}")
    print("Please double-check:")
    print(f"1. Is the FramePack Gradio app still running at {API_URL}?")
    print("2. ****** Did you fix the TypeError in demo_gradio.py and RESTART the server? ******")
    print("3. Are all parameters correctly formatted?")
    print("4. Does the input image path exist and is it accessible?")