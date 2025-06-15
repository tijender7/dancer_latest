import json
from pathlib import Path

# ✅ Configurable path to your workflow folder
workflow_dir = Path("D:/Comfy_UI_V20/ComfyUI/pysssss-workflows")

def list_workflows(path: Path):
    workflows = sorted(path.glob("*.json"))
    print(f"\n📁 Available Workflows in: {path}")
    for i, wf in enumerate(workflows, 1):
        print(f"[{i}] {wf.name}")
    return workflows

def inspect_workflow_inputs(workflow_path: Path):
    print(f"\n🔍 Inspecting Workflow: {workflow_path.name}")
    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading workflow JSON: {e}")
        return

    if isinstance(data, dict) and "nodes" in data and isinstance(data["nodes"], list):
        nodes = data["nodes"]
        print("✅ Detected wrapped workflow with 'nodes' array.")
    elif isinstance(data, dict):
        nodes = data
        print("✅ Detected flat workflow structure.")
    else:
        print("❌ Invalid workflow format (not dict or not wrapped properly).")
        return

    print(f"\n📊 Scanning {len(nodes)} nodes...\n")
    found = 0

    # Support both flat and wrapped
    for node_id, node in (nodes.items() if isinstance(nodes, dict) else enumerate(nodes)):
        if not isinstance(node, dict):
            print(f"⚠️  Node {node_id} skipped: not a dict (type={type(node)})")
            continue

        class_type = node.get("class_type", "")
        title = node.get("_meta", {}).get("title", "")
        inputs = node.get("inputs", {})

        print(f"🔍 Node ID: {node_id}")
        print(f"   🔧 Class Type: {class_type}")
        print(f"   🏷️  Title     : {title}")
        print(f"   📥 Inputs    : {json.dumps(inputs, indent=2) if isinstance(inputs, (dict, list)) else str(inputs)}")

        detected = False
        if isinstance(inputs, dict):
            for key in inputs.keys():
                if any(k in key.lower() for k in ["text", "prompt", "path", "file", "image", "audio"]):
                    print(f"✅ Detected user input field: {key}")
                    found += 1
                    detected = True
        elif isinstance(inputs, list):
            for inp in inputs:
                if isinstance(inp, dict):
                    name = inp.get("name", "")
                    if any(k in name.lower() for k in ["text", "prompt", "path", "file", "image", "audio"]):
                        print(f"✅ Detected user input field (list): {name}")
                        found += 1
                        detected = True
        if not detected:
            print("⚠️ Skipped: no user-related inputs found.")
        print("-" * 50)

    print("\n" + "=" * 50)
    if found == 0:
        print("⚠️ No user-input nodes found.")
    else:
        print(f"✅ Found {found} user input node(s).")

# -------- CLI Logic --------
workflows = list_workflows(workflow_dir)
if not workflows:
    print("❌ No workflows found.")
else:
    try:
        choice = int(input("\nEnter the number of the workflow to inspect: "))
        if 1 <= choice <= len(workflows):
            inspect_workflow_inputs(workflows[choice - 1])
        else:
            print("❌ Invalid selection.")
    except Exception as e:
        print(f"❌ Input error: {e}")
