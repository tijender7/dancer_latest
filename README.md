# Dancer Project 🕺💃

This repo contains automation scripts and workflows for generating, syncing, upscaling, and compiling AI-generated dance content using tools like ComfyUI, FFmpeg, and MoviePy.

## 📁 Structure

- `main_automation_*.py` – Entry points for different automation flows
- `api_server_*.py` – API endpoints and helpers
- `base_workflows/` – JSON workflow templates
- `sample_Audio/`, `source_faces/` – Input assets
- `output_*` – (ignored) generated outputs
- `venv/` – (ignored) virtual environment

## ⚙️ Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
