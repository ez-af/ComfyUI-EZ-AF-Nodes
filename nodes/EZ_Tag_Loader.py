from server import PromptServer  # type: ignore // ComfyUI Core
import os
import random
from aiohttp import web
import json

root_dir = os.path.dirname(os.path.abspath(__file__))
tags_path = os.path.abspath(os.path.join(root_dir, "../data/tags"))

class EZ_Tag_Loader:
    @classmethod
    def INPUT_TYPES(cls):
        global tags_path
        try:
            txt_files = []
            for root, dirs, files in os.walk(tags_path):
                for f in files:
                    if f.lower().endswith('.txt'):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, tags_path)
                        txt_files.append(rel_path)
        except Exception as e:
            txt_files = []

        return {
            "required": {
                "tags_file": (txt_files, {"tooltip": "Text file to search for tags"}),
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
                "prefix": ("STRING", {"default": "", "tooltip": "Add text string after each tag (comma-separated)"}),
                "suffix": ("STRING", {"default": "", "tooltip": "Add text string after each tag (comma-separated)"}),
                "selected_tags": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("STRING", "OPT_FILEPATH", "BATCH_SELECTED")
    OUTPUT_IS_LIST = (False, False, True)
    OUTPUT_TOOLTIPS = ("Selected tag(s).\nDelimited by comma if multiple","Path to currently selected text file containing tags.","List of all selected items.\nWill output all visible (filtered) items if none or single item is selected.")

    FUNCTION = "browse_tags"

    CATEGORY = "EZ NODES"
    DESCRIPTION = "Loads tags from selected text file based on UI selection."

    def browse_tags(self, tags_file, selection_mode="single", selected_tags="", filter_text="", prefix="", suffix="", opt_seed=0):
        global tags_path
        tags_file = os.path.join(tags_path, tags_file)
        tags_file = os.path.abspath(tags_file)

        if not os.path.isfile(tags_file):
            return ("No tags file found", tags_file, [])

        # Read tags from file
        with open(tags_file, "r", encoding="utf-8") as f:
            tags = []
            for line in f.readlines():
                line = line.strip()
                if not line:
                    continue
                if line == '[empty]':
                    tags.append("")
                else:
                    tags.append(line)

        if not tags:
            return ("No tags found in file", tags_file, [])

        # Filter tags if filter_text is provided
        if filter_text:
            tags = [tag for tag in tags if filter_text.lower() in tag.lower()]

        if not tags:
            return ("No matching tags found", tags_file, [])

        # Handle different selection modes
        selected_list = []
        if selection_mode == "random":
            # Use seed for deterministic random selection only if opt_seed is provided and not 0
            if opt_seed is not None and opt_seed != 0:
                random.seed(opt_seed)
            if selected_tags:
                selected_tags_list = [tag.strip() for tag in selected_tags.split(",")]
                valid_selected_tags = [tag for tag in selected_tags_list if tag in tags]
                if valid_selected_tags:
                    selected = random.choice(valid_selected_tags)
                else:
                    selected = random.choice(tags)
            else:
                selected = random.choice(tags)
            selected_list = [selected]
        elif selection_mode == "multiple":
            if selected_tags:
                selected_list = [tag.strip() for tag in selected_tags.split(",") if tag.strip() in tags]
        else:  # single
            if not selected_tags or selected_tags not in tags:
                selected_list = [tags[0]]
            else:
                selected_list = [selected_tags]

        # Add 'suffix' to each selected tag if provided
        #if suffix:
        #    selected_list = [suffix if tag == '' else f"{tag} , {suffix}" for tag in selected_list]
        #if prefix:
        #    selected_list = [prefix if tag == '' else f"{prefix}, {tag}" for tag in selected_list]
        # Main output
        main_output = ", ".join(selected_list)
        # Add Prefix       
        if prefix:
            main_output = [prefix if main_output == '' else f"{prefix}, {main_output}"]
        # Add Suffix           
        if suffix:    
            main_output = [suffix if main_output == '' else f"{main_output[0]}, {suffix}"]        

        # Add Prefix
        if len(selected_list) == 0 and prefix:
            all_output = [prefix]
        elif len(selected_list) > 0 and prefix:
            all_output = [prefix if tag == '' else f"{prefix}, {tag}" for tag in selected_list]
        else:
            all_output = selected_list
        # Add Suffix
        if len(all_output) == 0 and suffix:                   
            all_output = [suffix]
        elif len(all_output) > 0 and suffix:                   
            all_output = [suffix if tag == '' else f"{tag}, {suffix}" for tag in all_output]
        return (main_output, tags_file, all_output)

    @classmethod
    def IS_CHANGED(cls, tags_file, selection_mode, selected_tags="", filter_text="", suffix="", opt_seed=0):
        if selection_mode == "random":
            # For random mode, include seed in the hash only if opt_seed is provided and not 0
            if opt_seed is not None and opt_seed != 0:
                return str(opt_seed) + str(tags_file) + str(selection_mode) + str(filter_text)
            else:
                return float('nan')  # Fall back to normal random behavior
        return selected_tags + str(tags_file) + str(selection_mode) + str(suffix)

    @classmethod
    def VALIDATE_INPUTS(cls, tags_file, selection_mode="single", selected_tags="", filter_text="", suffix="", opt_seed=0):
        global tags_path
        tags_file = os.path.join(tags_path, tags_file)
        tags_file = os.path.abspath(tags_file)
        if not os.path.isfile(tags_file):
            return "Tags file does not exist"
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

def get_tags_from_file(file_path, filter_text=""):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tags = []
            for line in f.readlines():
                line = line.strip()
                if not line:
                    continue
                if line == '[empty]':
                    tags.append("")
                else:
                    tags.append(line)
            # Apply filter if provided
            if filter_text:
                filter_text = filter_text.lower()
                tags = [tag for tag in tags if filter_text in tag.lower()]
            return tags
    except Exception as e:
        print(f"Error reading tags file {file_path}: {e}")
        return []

@PromptServer.instance.routes.post("/ez_tag_browser/get_directory_structure")
async def api_get_directory_structure(request):
    try:
        data = await request.json()
        path = data.get("path", "./")
        filter_text = data.get("filter", "")

        if not os.path.isabs(path):
            path = os.path.abspath(path)

        if not os.path.exists(path):
            return web.json_response({"error": "Path does not exist"}, status=400)

        # If path is a file, get its directory
        if os.path.isfile(path):
            directory = os.path.dirname(path)
            structure = get_directory_structure(directory)
            tags = get_tags_from_file(path, filter_text)
        else:
            structure = get_directory_structure(path)
            tags = []

        response_data = {
            "structure": structure,
            "tags": tags
        }
        
        return web.json_response(response_data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

@PromptServer.instance.routes.post("/ez_tag_browser/get_file_info")
async def get_file_info(request):
    try:
        data = await request.json()
        rel_path = data.get("relative_path", "")
        
        full_path = os.path.normpath(os.path.join(tags_path, rel_path))
        if not full_path.startswith(tags_path):
            return web.json_response({"error": "Invalid path"}, status=400)

        if not os.path.exists(full_path):
            return web.json_response({"error": "File not found"}, status=404)

        return web.json_response({
            "full_path": full_path,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
