from server import PromptServer  # type: ignore // ComfyUI Core
import os
from PIL import Image
from aiohttp import web
import io
import random

root_dir = os.path.dirname(os.path.abspath(__file__))
prompts_path = os.path.abspath(os.path.join(root_dir, "../data/prompts"))

class EZ_Prompt_Loader:
    @classmethod
    def INPUT_TYPES(cls):
        global prompts_path
        try:
            prompt_dirs = []
            for root, dirs, files in os.walk(prompts_path):
                for d in dirs:
                    full_path = os.path.join(root, d)
                    rel_path = os.path.relpath(full_path, prompts_path)
                    prompt_dirs.append(rel_path)
        except Exception:
            prompt_dirs = []

        return {
            "required": {
                "prompt_directory": (prompt_dirs, {"tooltip": "Directory to search for prompt files.\nSearches recursively through all subdirectories."}),
                "selection_mode": (["single", "multiple", "random"], {"default": "single", "tooltip":
                                                                        "- single: Allows selection of one item at a time.\n"
                                                                        "- multiple: Allows selection of multiple items. Output will be comma-separated.\n"
                                                                        "- random: Allows selection of multiple items. Randomly outputs one of the selected items on each prompt queue."
                                                                        " Will select from all visible (filtered) items if none or single item is selected."
                                                                        " Uses seed if opt_seed is connected. Always re-executes node if opt_seed is not connected"}),
            },
            "optional": {
                "opt_seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True, "tooltip": "Control SEED, used only in 'random' selection mode.\nIf not connected, always re-executes node on prompt"}),
                "filter_text": ("STRING", {"default": "", "tooltip": "Filter items based on a text string"}),
                "prefix": ("STRING", {"default": "", "tooltip": "Add text string before each tag (comma-separated)"}),
                "suffix": ("STRING", {"default": "", "tooltip": "Add text string after each tag (comma-separated)"}),
                "selected_files": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("STRING", "OPT_DIRECTORY", "BATCH_SELECTED")
    OUTPUT_IS_LIST = (False, False, True)
    OUTPUT_TOOLTIPS = ("Content of selected prompt file(s).\nDelimited by comma if multiple","Path to currently selected directory.","List of all selected items.\nWill output all visible (filtered) items if none or single item is selected.")

    FUNCTION = "browse_files"

    CATEGORY = "EZ NODES"
    DESCRIPTION = "Loads prompt texts from files based on UI selection.\nSearches recursively through all subdirectories within the selected folder."

    def browse_files(self, prompt_directory, selection_mode="single", selected_files="", filter_text="", prefix="", suffix="", opt_seed=0):
        global prompts_path
        prompt_directory = os.path.join(prompts_path, prompt_directory)
        prompt_directory = os.path.abspath(prompt_directory)

        # List text files
        files = get_file_list(prompt_directory, filter_text)

        if not files:
            return ("No corresponding files found", prompt_directory, [])

        # Handle different selection types
        selected_list = []
        if selection_mode == "random":
            # Use seed for deterministic random selection only if opt_seed is provided and not 0
            if opt_seed is not None and opt_seed != 0:
                random.seed(opt_seed)
            if selected_files:
                selected_files_list = [f.strip() for f in selected_files.split(",")]
                valid_selected_files = [f for f in selected_files_list if f in files]
                if valid_selected_files:
                    selected = random.choice(valid_selected_files)
                else:
                    selected = random.choice(files)
            else:
                selected = random.choice(files)
            selected_list = [selected]
        elif selection_mode == "multiple":
            if selected_files:
                selected_list = [f.strip() for f in selected_files.split(",") if f.strip() in files]
        else:  # single
            if not selected_files or selected_files not in files:
                selected_list = [files[0]]
            else:
                selected_list = [selected_files]

        # Main output
        if selection_mode == "multiple":
            prompt_texts = []
            for file in selected_list:
                file = file.strip()
                if file in files:
                    txt_path = os.path.join(prompt_directory, file)
                    if os.path.isfile(txt_path):
                        with open(txt_path, "r", encoding="utf-8") as f:
                            prompt_texts.append(f.read().strip())
            prompt_text = ", ".join(prompt_texts)
        else:
            txt_path = os.path.join(prompt_directory, selected_list[0])
            prompt_text = ""
            if os.path.isfile(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    prompt_text = f.read().strip()
        if prefix:
            prompt_text = [prefix if prompt_text == '' else f"{prefix}, {prompt_text}"]
        # Add Suffix           
        if prefix and suffix:    
            prompt_text = [suffix if prompt_text == '' else f"{prompt_text[0]}, {suffix}"]
        elif not prefix and suffix:   
            prompt_text = [suffix if prompt_text == '' else f"{prompt_text}, {suffix}"]            
            
        # List output: if 0 or 1 selected, output all prompts; else output selected_list
        if len(selected_list) < 1:
            all_output = []
            for file in files:
                txt_path = os.path.join(prompt_directory, file)
                if os.path.isfile(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        all_output.append(f.read().strip())
        else:
            all_output = []
            for file in selected_list:
                txt_path = os.path.join(prompt_directory, file)
                if os.path.isfile(txt_path):
                    with open(txt_path, "r", encoding="utf-8") as f:
                        all_output.append(f.read().strip())

        # Add Prefix
        if prefix:
            all_output = [prefix if tag == '' else f"{prefix}, {tag}" for tag in all_output]
        # Add Suffix
        if suffix:                   
            all_output = [suffix if tag == '' else f"{tag}, {suffix}" for tag in all_output]

        return (prompt_text, prompt_directory, all_output)

    @classmethod
    def IS_CHANGED(cls, prompt_directory, selection_mode, selected_files="", filter_text="", opt_seed=0):
        if selection_mode == "random":
            # For random mode, include seed in the hash only if opt_seed is provided and not 0
            if opt_seed is not None and opt_seed != 0:
                return str(opt_seed) + str(prompt_directory) + str(selection_mode) + str(filter_text)
            else:
                return float('nan')  # Fall back to normal random behavior
        return selected_files + str(prompt_directory) + str(selection_mode)

    @classmethod
    def VALIDATE_INPUTS(cls, prompt_directory, selection_mode="single", selected_files="", filter_text="", opt_seed=0):
        global prompts_path
        prompt_directory = os.path.join(prompts_path, prompt_directory)
        prompt_directory = os.path.abspath(prompt_directory)
        if not os.path.isdir(prompt_directory):
            return "Root directory does not exist"
        if selected_files:
            for file in selected_files.split(","):
                file = file.strip()
                if file:
                    file_path = os.path.join(prompt_directory, file)
                    if not os.path.isfile(file_path):
                        return f"Selected file {file} does not exist"
        return True


def get_directory_structure(path):
    structure = {"name": os.path.basename(path), "children": [], "path": path, "expanded": False}
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_dir():
                    structure["children"].append(get_directory_structure(entry.path))
    except PermissionError:
        pass
    return structure

def get_file_list(path, filter_text=""):
    result = []
    filter_text = (filter_text or "").lower()

    # Recursively walk through all subdirectories
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.lower().endswith(".txt"):
                base_name = os.path.splitext(f)[0]

                if filter_text and filter_text not in base_name.lower():
                    continue

                # Get relative path from the root directory
                rel_path = os.path.relpath(os.path.join(root, f), path)
                result.append(rel_path)

    return result


@PromptServer.instance.routes.post("/ez_file_browser/get_directory_structure")
async def api_get_directory_structure(request):
    data = await request.json()
    path = data.get("path", "./")
    filter_text = data.get("filter", "")

    if not os.path.isabs(path):
        path = os.path.abspath(path)

    if not os.path.exists(path):
        return web.json_response({"error": "Directory does not exist"}, status=400)

    structure = get_directory_structure(path)
    files = get_file_list(path, filter_text)
    return web.json_response({"structure": structure, "files": files})


@PromptServer.instance.routes.post("/ez_file_browser/get_thumbnail")
async def api_get_thumbnail(request):
    data = await request.json()
    path = data.get("path", "./")
    file = data.get("file", "")

    if not os.path.isabs(path):
        path = os.path.abspath(path)

    full_path = os.path.join(path, file)
    if not os.path.exists(full_path):
        return web.json_response({"error": "File does not exist"}, status=400)

    try:
        with Image.open(full_path) as img:
            img.thumbnail((256,256))
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return web.Response(body=buf.read(), content_type='image/png')
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
    
@PromptServer.instance.routes.post("/ez_file_browser/get_file_info")
async def get_file_info(request):
    # global prompts_path
    # prompt_directory = os.path.join(prompts_path, prompt_directory)
    # return web.json_response({
    #     "full_path": prompt_directory,
    # })
    data = await request.json()
    rel_path = data.get("relative_path", "")
    
    full_path = os.path.normpath(os.path.join(prompts_path, rel_path))
    if not full_path.startswith(prompts_path):
        return web.json_response({"error": "Invalid path"}, status=400)

    if not os.path.exists(full_path):
        return web.json_response({"error": "File not found"}, status=404)

    return web.json_response({
        "full_path": full_path,
    })
