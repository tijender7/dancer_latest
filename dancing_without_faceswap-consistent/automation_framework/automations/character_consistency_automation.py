import logging
import random
import shutil
import subprocess
import threading
import json
import sys
import time
from pathlib import Path
from tqdm import tqdm

try:
    from flask import Flask, request, render_template_string, send_from_directory, url_for
except ImportError:
    Flask = None

from .base_automation import BaseAutomation

logger = logging.getLogger(__name__)

# --- Prompt Components ---
PROMPT_LOCATIONS = ["a busy construction site", "a traditional Indian household kitchen", "a modern office building", "a bustling Indian marketplace", "a hospital or clinic", "a school classroom"]
PROMPT_ATTIRES = ["a sexy, revealing maid outfit with tiny skirt and low-cut top", "a provocative construction worker costume with cropped tank top and tiny shorts", "a revealing secretary outfit with short tight skirt and unbuttoned blouse", "a sexy nurse costume with mini dress and low neckline", "a seductive teacher outfit with short skirt and tight-fitting top", "a revealing shop worker uniform with tiny apron and skimpy clothes"]
BODY_TYPE_PROMPTS = ["a very slim and athletic build", "an hourglass figure", "a slightly chubby and soft body", "a voluptuous and curvy figure", "a pear-shaped body", "extremely large natural breasts", "a toned and muscular physique"]

# --- Approval Server (Flask App) ---
if Flask:
    approval_app = Flask(__name__)
    approval_data = {}

    @approval_app.route('/')
    def index():
        global approval_data
        items_html = ""
        for item in approval_data.get("items_for_approval", []):
            img_path = Path(item["image_path"])
            try:
                relative_path = img_path.relative_to(approval_data["comfyui_output_base"]).as_posix()
                img_src = url_for('serve_image', filename=relative_path)
                items_html += f"""
                <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; display: inline-block; vertical-align: top;">
                    <p><b>ID: {item.get('approval_id', 'N/A')}</b></p>
                    <img src="{img_src}" alt="Generated Image" style="max-width: 256px; max-height: 256px;"><br>
                    <input type="checkbox" name="approved_item" value="{item['approval_id']}"> Approve
                </div>"""
            except ValueError:
                logger.warning(f"Could not create relative path for {img_path}. Skipping in UI.")
        
        html_content = f"""
        <!DOCTYPE html><html><head><title>{approval_data.get('phase_name')}</title></head><body>
        <h1>{approval_data.get('phase_name')}</h1>
        <p>You can approve up to <b>{approval_data.get('max_approvals', 'N/A')}</b> images.</p>
        <form action="/submit" method="post">{items_html}<br><button type="submit" style="margin-top:20px;">Submit Approvals</button></form>
        </body></html>"""
        return render_template_string(html_content)

    @approval_app.route('/images/<path:filename>')
    def serve_image(filename):
        return send_from_directory(approval_data["comfyui_output_base"], filename)

    @approval_app.route('/submit', methods=['POST'])
    def submit_approval():
        approved_ids = request.form.getlist('approved_item')
        approved_items = [item for item in approval_data["items_for_approval"] if item.get("approval_id") in approved_ids]
        with open(approval_data["approval_file_path"], 'w', encoding='utf-8') as f:
            json.dump(approved_items, f, indent=2, default=str)
        logger.info(f"Web UI approvals saved to {approval_data['approval_file_path']}.")
        if "shutdown_event" in approval_data:
             approval_data["shutdown_event"].set()
        return "Approvals submitted! You can close this window."

class CharacterConsistencyAutomation(BaseAutomation):
    def __init__(self, config_path: str, comfyui_input_dir: str, comfyui_output_dir: str):
        super().__init__(config_path)
        self.comfyui_input_dir = Path(comfyui_input_dir)
        self.comfyui_output_dir = Path(comfyui_output_dir)
        if not self.comfyui_input_dir.is_dir() or not self.comfyui_output_dir.is_dir():
            raise FileNotFoundError("ComfyUI input or output directory not found.")
        self.temp_dir_path = self.comfyui_input_dir / self.temp_dir_name
        self.action_prompts = self._load_action_prompts()
        self.main_run_folder = self.output_folder / f"Run_{self.run_timestamp}"
        self.main_run_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Main run folder created at: {self.main_run_folder}")

    def _load_action_prompts(self):
        prompts_path = self.script_dir / "action_prompts.txt"
        try:
            with open(prompts_path, 'r') as f: return [line.strip() for line in f if line.strip()]
        except FileNotFoundError: return ["dancing gracefully"]
    
    def _extract_character_id_from_approval_id(self, approval_id: str) -> str:
        """Extract character ID from approval_id 
        
        Examples:
        - Phase 1: '1-1' -> '1' 
        - Phase 2: '1-2-1' -> '1' (character-expansion-variation)
        - Phase 3: '1-2-1' -> '1'
        """
        if '-' in approval_id:
            return approval_id.split('-')[0]
        return approval_id

    def _generate_phase1_prompts(self):
        logger.info("--- Generating Phase 1 (Seeding) Prompts ---")
        prompts = []
        num_seeds = self.config.get("phase1_num_seed_images", 7)
        selected_location = random.choice(PROMPT_LOCATIONS)
        selected_attire = random.choice(PROMPT_ATTIRES)
        logger.info(f"Run Theme - Location: '{selected_location}', Attire: '{selected_attire}'")
        for i in range(num_seeds):
            body_type = BODY_TYPE_PROMPTS[i % len(BODY_TYPE_PROMPTS)]
            full_prompt = (
                f"cinematic photo of a beautiful Indian woman with {body_type}, "
                f"very big boobs and hips, wearing revealing clothes, specifically {selected_attire}. "
                f"She is at {selected_location}. Sexy pose, seductive appearance, dynamic pose, professional lighting, 8k, natural skin tones, balanced color grading. "
                f"BREAK "
                f"bad quality, blurry, sepia, yellow tint, oversaturated, monochrome, watermark, text, signature, "
                f"nude, nudity, nipples, pussy, bare chest, topless, explicit."
            )
            prompts.append({"display_index": i + 1, "prompt": full_prompt})
        return prompts

    def _execute_generation_and_polling(self, phase_name: str, generation_list: list[dict], endpoint: str, character_aware: bool = False):
        for item in tqdm(generation_list, desc=f"{phase_name}: Submitting Jobs"):
            # Create character-aware subfolder if requested
            if character_aware and "character_id" in item:
                comfyui_subfolder = f"Run_{self.run_timestamp}/{phase_name}/character_{item['character_id']}"
            else:
                comfyui_subfolder = f"Run_{self.run_timestamp}/{phase_name}"
            
            prefix = item.get("filename_prefix", f"{phase_name}_{item['display_index']:03d}")
            payload = { "prompt": item["prompt"], "output_subfolder": comfyui_subfolder, "filename_prefix_text": prefix }
            if "reference_image_path" in item:
                payload["reference_image_path"] = item["reference_image_path"]
            item["job_prompt_id"] = self.trigger_generation(endpoint, payload)
            item["job_status"] = "submitted" if item["job_prompt_id"] else "failed"

    def _poll_and_unroll_batches(self, phase_name, generation_list):
        logger.info(f"\n--- Polling for {phase_name} completion... ---")
        unrolled_images = []
        for item in tqdm(generation_list, desc=f"{phase_name}: Polling Jobs"):
            if not item.get("job_prompt_id"): continue
            history = self.poll_for_job_completion(item["job_prompt_id"])
            if not history:
                item["job_status"] = "polling_timeout"; continue
            item["job_status"] = "completed"
            item["generated_image_paths"] = self.get_output_filenames_from_history(history)
            for i, image_path in enumerate(item["generated_image_paths"]):
                # For Phase 2 expansions, inherit character ID from parent seed
                if "character_id" in item and phase_name == "phase2_expansion":
                    approval_id = f"{item['character_id']}-{item['display_index']}-{i+1}"
                else:
                    # For Phase 1 seeds, use original logic
                    approval_id = f"{item['display_index']}-{i+1}"
                
                unrolled_images.append({
                    "approval_id": approval_id,
                    "image_path": str(image_path),
                    "original_prompt_data": item
                })
        return unrolled_images

    def _run_parallel_approval(self, phase_name: str, items_for_approval: list[dict], max_approvals: int):
        logger.info(f"\n--- Starting Parallel Approval: {phase_name} ---")
        web_approval_file = self.main_run_folder / f"web_approvals_{phase_name.lower().replace(' ', '_')}.json"
        telegram_script_path = self.script_dir / "send_telegram_image_approvals.py"
        
        telegram_dir = self.script_dir / "telegram_approvals"
        telegram_dir.mkdir(exist_ok=True)
        telegram_approvals_json = self.script_dir / "telegram_approvals.json"
        
        # Clean up old state files for this phase
        if web_approval_file.exists(): web_approval_file.unlink()
        if telegram_approvals_json.exists(): telegram_approvals_json.unlink()
        if (telegram_dir / "token_map.json").exists(): (telegram_dir / "token_map.json").unlink()

        # --- Web UI Thread ---
        shutdown_event = threading.Event()
        flask_thread = None
        if self.config.get("enable_web_approval") and Flask:
            global approval_data
            approval_data.update({
                "items_for_approval": items_for_approval,
                "comfyui_output_base": self.comfyui_output_dir,
                "approval_file_path": web_approval_file,
                "shutdown_event": shutdown_event,
                "phase_name": phase_name,
                "max_approvals": max_approvals
            })
            flask_thread = threading.Thread(target=approval_app.run, kwargs={"host": "0.0.0.0", "port": 5005, "debug": False}, daemon=True)
            flask_thread.start()
            logger.info("Flask Web UI for approval started at http://localhost:5005")
        
        # --- Telegram Process ---
        telegram_process = None
        if self.config.get("enable_telegram_approval") and telegram_script_path.is_file():
            image_paths = [item["image_path"] for item in items_for_approval]
            try:
                telegram_process = subprocess.Popen([sys.executable, str(telegram_script_path)] + image_paths)
                logger.info("Telegram approval process started in a separate process.")
            except Exception as e:
                logger.error(f"Failed to start Telegram approval script: {e}")

        print(f"\n{'='*60}\n APPROVAL REQUIRED: {phase_name}\n  - Web UI:  http://localhost:5005\n  - Telegram: Check your bot.\n{'='*60}")
        
        # --- Wait for an approval result from either method ---
        while True:
            # Check for Web UI completion first
            if web_approval_file.exists():
                logger.info("Web UI approval detected.")
                logger.debug(f"Web approval file found at: {web_approval_file}")
                if telegram_process and telegram_process.poll() is None:
                    logger.info("Shutting down pending Telegram process...")
                    telegram_process.terminate()
                with open(web_approval_file, 'r') as f:
                    approved_items = json.load(f)[:max_approvals]
                    logger.info(f"Loaded {len(approved_items)} approved items from web UI")
                    return approved_items
            
            # Then, check if the Telegram process has finished
            if telegram_process and telegram_process.poll() is not None:
                logger.info("Telegram process has finished.")
                logger.debug(f"Checking for Telegram approval file at: {telegram_approvals_json}")
                if telegram_approvals_json.exists():
                    logger.info("Processing Telegram approval file...")
                    try:
                        with open(telegram_approvals_json, 'r') as f: tg_results = json.load(f)
                        logger.debug(f"Telegram results: {len(tg_results)} entries")
                        approved_paths = {Path(p).resolve() for p, info in tg_results.items() if info.get("status") == "approve"}
                        approved_items = [item for item in items_for_approval if Path(item["image_path"]).resolve() in approved_paths]
                        logger.info(f"Telegram approval: {len(approved_items)} items approved out of {len(items_for_approval)} total")
                        if flask_thread and flask_thread.is_alive(): shutdown_event.set()
                        return approved_items[:max_approvals]
                    except Exception as e:
                        logger.error(f"Error processing Telegram approval file: {e}")
                        break
                else:
                    logger.warning(f"Telegram process finished but no approval file was found at: {telegram_approvals_json}")
                    break

            if not flask_thread and not telegram_process: break
            if shutdown_event.is_set(): return [] # Web UI was closed without submission
            time.sleep(2)

        # Fallback if loop is broken
        logger.warning("Approval loop exited without a result.")
        if flask_thread and flask_thread.is_alive(): shutdown_event.set()
        if telegram_process and telegram_process.poll() is None: telegram_process.terminate()
        return []


    def run(self):
        logger.info("=" * 50); logger.info("🚀 STARTING CHARACTER CONSISTENCY AUTOMATION"); logger.info("=" * 50)
        self.temp_dir_path.mkdir(exist_ok=True)

        # === STAGE 1: SEEDING ===
        phase1_prompts = self._generate_phase1_prompts()
        self._execute_generation_and_polling("phase1_seeds", phase1_prompts, "generate_seeding_image")
        unrolled_phase1_images = self._poll_and_unroll_batches("phase1_seeds", phase1_prompts)
        
        approved_seeds = self._run_parallel_approval("Phase 1: Select Character Seed(s)", unrolled_phase1_images, self.config.get("phase1_max_approvals", 3))
        if not approved_seeds: logger.warning("No seeds approved. Stopping."); return

        # === STAGE 2: EXPANSION ===
        phase2_generation_list = []
        for seed_data in approved_seeds:
            ref_image_path = Path(seed_data["image_path"])
            ref_filename = f"ref_{seed_data['approval_id']}.png"
            temp_path = self.temp_dir_path / ref_filename
            shutil.copy(ref_image_path, temp_path)
            comfy_ref_path = f"{self.temp_dir_name}/{ref_filename}"
            num_to_gen = self.config.get("phase2_num_expansion_images_per_seed", 20)
            selected_actions = random.sample(self.action_prompts, min(num_to_gen, len(self.action_prompts)))
            
            # Extract character ID for character-aware folder structure
            character_id = self._extract_character_id_from_approval_id(seed_data['approval_id'])
            logger.info(f"📁 Character {character_id}: Generating {len(selected_actions)} expansion images")
            
            # Use character-specific display index for proper inheritance
            character_expansion_index = 1
            for action_prompt in selected_actions:
                phase2_generation_list.append({ 
                    "display_index": character_expansion_index,  # Character-specific index for proper approval_id inheritance
                    "prompt": action_prompt, 
                    "reference_image_path": comfy_ref_path, 
                    "original_prompt_data": seed_data["original_prompt_data"],
                    "action_prompt": action_prompt,  # Store action prompt for video generation
                    "character_id": character_id,  # Store character ID for folder organization
                    "seed_approval_id": seed_data['approval_id']  # Store original seed approval ID
                })
                character_expansion_index += 1
        self._execute_generation_and_polling("phase2_expansion", phase2_generation_list, "generate_expansion_image", character_aware=True)
        unrolled_phase2_images = self._poll_and_unroll_batches("phase2_expansion", phase2_generation_list)
        approved_for_video = self._run_parallel_approval("Phase 2: Approve Final Images for Video", unrolled_phase2_images, max_approvals=len(unrolled_phase2_images))

        # === STAGE 3: VIDEO GENERATION ===
        if approved_for_video:
            logger.info(f"\n--- STAGE 3: VIDEO GENERATION for {len(approved_for_video)} images ---")
            video_generation_list = []
            
            # Group videos by character for better logging
            character_video_count = {}
            
            for i, item in enumerate(approved_for_video):
                img_path = Path(item["image_path"])
                vid_start_fn = f"vid_start_{item['approval_id']}.png"
                temp_path = self.temp_dir_path / vid_start_fn
                shutil.copy(img_path, temp_path)
                logger.debug(f"Copied video start image: {img_path} -> {temp_path}")
                
                # Use action prompt for dancing videos instead of static prompt
                action_prompt = item["original_prompt_data"].get("action_prompt", "dancing gracefully")
                video_prompt = f"A beautiful Indian woman {action_prompt}, smooth motion, dynamic movement, cinematic lighting"
                logger.debug(f"Video prompt for {item['approval_id']}: {action_prompt}")
                
                # Extract character ID for character-aware folder structure
                character_id = self._extract_character_id_from_approval_id(item['approval_id'])
                character_video_count[character_id] = character_video_count.get(character_id, 0) + 1
                
                video_generation_list.append({
                    "display_index": i + 1,
                    "prompt": video_prompt, 
                    "reference_image_path": f"{self.temp_dir_name}/{vid_start_fn}",
                    "filename_prefix": f"video_{item['approval_id']}",
                    "character_id": character_id  # Store character ID for folder organization
                })
            
            # Log character distribution
            logger.info(f"🎭 Video distribution by character: {dict(sorted(character_video_count.items()))}")
            
            logger.info(f"📤 Submitting {len(video_generation_list)} video generation jobs...")
            self._execute_generation_and_polling("phase3_videos", video_generation_list, "generate_video", character_aware=True)
            logger.info("⏳ Polling for video generation completion (this may take several minutes)...")
            unrolled_video_results = self._poll_and_unroll_batches("phase3_videos", video_generation_list)
            logger.info(f"✅ Generated {len(unrolled_video_results)} videos successfully")
            logger.info(f"📁 Videos automatically organized in character-specific folders")
        else:
            logger.warning("❌ No images approved for video generation. Skipping Stage 3.")

        if self.temp_dir_path.exists(): shutil.rmtree(self.temp_dir_path)
        logger.info("\n" + "="*50); logger.info("✅ AUTOMATION FINISHED SUCCESSFULLY"); logger.info("="*50)